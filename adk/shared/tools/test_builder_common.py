"""Utilitários compartilhados pelos construtores de testes pytest.

Este módulo concentra a normalização de requisitos, o tratamento de anexos,
a validação de código e os utilitários de filesystem usados tanto pelo agente
de testes unitários quanto pelo agente de testes de integração.
"""

import ast
import asyncio
import base64
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from litellm import completion

from shared.workspace import get_agent_workspace

logger = logging.getLogger("test_builder_common")


def _run_async(coro):
    """Executa coroutine de forma segura com ou sem event loop ativo.

    Args:
        coro: Coroutine a ser executada.

    Returns:
        Resultado da coroutine.

    Note:
        Compatível com FastAPI + ADK - usa ThreadPoolExecutor se houver loop ativo.
    """
    try:
        asyncio.get_running_loop()
        # Há um loop rodando (FastAPI/ADK) — executa em thread separada
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # Sem loop rodando — pode usar asyncio.run normalmente
        return asyncio.run(coro)

def _parse_fragmented_requirements(raw_input: str) -> list:
    """Converte texto livre/fragmentado em uma lista estruturada de artefatos."""
    prompt = f"""Extraia os requisitos do texto abaixo e retorne um JSON array estrito no formato:
[{{ "id_artefato": "RF-001", "tipo": "RF", "conteudo": "...", "modulo": "...", "criticidade": "alta|media|baixa" }}]
Identifique os tipos (RF, RNF, HU, UC, RN). Se não houver ID claro, gere um sequencial.
Texto bruto: {raw_input}
"""
    model_name = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")
    llm_kwargs = {}
    if "/" not in model_name:
        model_name = f"gemini/{model_name}"
        llm_kwargs["api_key"] = os.environ.get("GOOGLE_API_KEY")
    response = completion(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        **llm_kwargs,
    )
    
    conteudo = response.choices[0].message.content.strip()
    # Limpa possíveis formatações markdown do retorno do LLM
    if conteudo.startswith("```json"):
        conteudo = conteudo.replace("```json\n", "").replace("```", "")
    return json.loads(conteudo)

def _extrair_de_parts(parts: list) -> tuple[list[dict], list[str]]:
    arquivos_apoio: list[dict] = []
    textos: list[str] = []

    for part in parts:
        if not isinstance(part, dict):
            continue

        texto = part.get("text")
        if isinstance(texto, str) and texto.strip():
            textos.append(texto.strip())

        inline = part.get("inlineData")
        if not isinstance(inline, dict):
            continue

        nome = inline.get("displayName") or inline.get("name") or "arquivo_anexo"
        mime = inline.get("mimeType") or "application/octet-stream"
        conteudo_b64 = inline.get("data")
        if not isinstance(conteudo_b64, str) or not conteudo_b64.strip():
            continue

        entrada_arquivo = {"nome": nome}
        try:
            bruto = base64.b64decode(conteudo_b64)
            texto_decodificado = bruto.decode("utf-8")
            entrada_arquivo["conteudo"] = texto_decodificado
            if texto_decodificado.strip():
                textos.append(texto_decodificado.strip())
        except Exception:
            entrada_arquivo["conteudo_base64"] = conteudo_b64

        entrada_arquivo["mime_type"] = mime
        arquivos_apoio.append(entrada_arquivo)

    return arquivos_apoio, textos

def _normalizar_anexos_inline(lista_artefatos: list) -> list:
    normalizados = []
    for artefato in lista_artefatos:
        if not isinstance(artefato, dict):
            continue

        arquivos_existentes = artefato.get("arquivos_apoio", [])
        if not isinstance(arquivos_existentes, list):
            arquivos_existentes = []

        parts = artefato.get("parts")
        if not isinstance(parts, list):
            content = artefato.get("content", {})
            if isinstance(content, dict):
                parts = content.get("parts")

        textos_extraidos: list[str] = []
        if isinstance(parts, list):
            arquivos_extraidos, textos_extraidos = _extrair_de_parts(parts)
            arquivos_existentes.extend(arquivos_extraidos)

        if arquivos_existentes:
            artefato["arquivos_apoio"] = arquivos_existentes

        conteudo_atual = artefato.get("conteudo", "")
        if not isinstance(conteudo_atual, str):
            conteudo_atual = str(conteudo_atual)

        if textos_extraidos:
            bloco_extra = "\n\n".join(textos_extraidos).strip()
            if bloco_extra and bloco_extra not in conteudo_atual:
                artefato["conteudo"] = (
                    f"{conteudo_atual}\n\n{bloco_extra}".strip()
                    if conteudo_atual.strip()
                    else bloco_extra
                )

        normalizados.append(artefato)

    return normalizados

def _validar_e_sanitizar_codigo(codigo: str, id_artefato: str) -> str:
    """Sanitiza tokens fora-da-gramática Python e valida via ast.parse.

    Aplica regex que remove placeholders entre `<>` colocados após keywords
    Python (pass<X>, return<Y>, etc.) e em seguida valida o código com
    ast.parse. Se mesmo após sanitização o código permanece inválido,
    levanta ValueError — o chamador propaga o erro para o autocorrect cycle.

    Args:
        codigo: String com código Python emitido pelo LLM.
        id_artefato: ID do artefato (usado nas mensagens de log/erro).

    Returns:
        Código Python sanitizado e validado.

    Raises:
        ValueError: Se ast.parse falha após sanitização.
    """
    padrao = re.compile(r'\b(pass|return|continue|break|raise)<[^>\n]*>')
    sanitizado = padrao.sub(r'\1', codigo)

    if sanitizado != codigo:
        logger.warning(
            f"[QA] Sanitização aplicada em {id_artefato}: "
            f"removidos placeholders fora da gramática Python."
        )

    try:
        ast.parse(sanitizado)
    except SyntaxError as e:
        raise ValueError(
            f"Código gerado para {id_artefato} é inválido após sanitização: "
            f"{e.msg} (linha {e.lineno}). Será reciclado via autocorrect."
        ) from e

    return sanitizado

def _validar_artefato(artefato: dict) -> str | None:
    """Valida artefato de requisito verificando campos obrigatórios.

    Args:
        artefato: Dicionário com campos do artefato.

    Returns:
        str | None: Descrição do bloqueio ou None se válido.
    """
    if not artefato.get("conteudo", "").strip():
        return "Campo 'conteudo' vazio — impossível gerar testes sem descrição do requisito."
    if not artefato.get("modulo", "").strip():
        artefato["modulo"] = "geral"
    if artefato.get("tipo") not in ("RF", "HU", "UC", "RNF", "RN"):
        return (
            f"Tipo desconhecido: '{artefato.get('tipo')}'. "
            "Esperado: RF, HU, UC, RNF ou RN."
        )
    return None

def _slugify(texto: str) -> str:
    """Normaliza texto para uso em nomes de arquivo.

    Args:
        texto: Texto a normalizar.

    Returns:
        str: Slug seguro para nomes de arquivo.
    """
    base = (texto or "artefato").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = base.strip("_")
    return base or "artefato"

def _safe_filename(nome: str) -> str:
    """Sanitiza nome de arquivo removendo caracteres especiais.

    Args:
        nome: Nome original do arquivo.

    Returns:
        str: Nome seguro para filesystem.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", (nome or "arquivo.txt").strip())
    cleaned = cleaned.lstrip(".")
    return cleaned or "arquivo.txt"

def _salvar_arquivos_apoio(artefato: dict, destino: Path) -> list[Path]:
    """Salva arquivos de apoio (texto ou base64) no diretório de destino.

    Args:
        artefato: Dicionário contendo lista de arquivos_apoio.
        destino: Path do diretório onde arquivos serão salvos.

    Returns:
        list[Path]: Lista de paths dos arquivos salvos.
    """
    arquivos = artefato.get("arquivos_apoio", [])
    if not isinstance(arquivos, list):
        return []

    salvos: list[Path] = []
    for item in arquivos:
        if not isinstance(item, dict):
            continue

        nome = _safe_filename(item.get("nome") or item.get("filename") or "arquivo.txt")
        conteudo_texto = item.get("conteudo")
        conteudo_b64 = item.get("conteudo_base64")

        caminho = destino / nome

        if isinstance(conteudo_texto, str):
            caminho.write_text(conteudo_texto, encoding="utf-8")
            salvos.append(caminho)
            continue

        if isinstance(conteudo_b64, str):
            try:
                bruto = base64.b64decode(conteudo_b64)
            except Exception:
                continue
            caminho.write_bytes(bruto)
            salvos.append(caminho)

    return salvos

def _ordenar_por_criticidade(lista: list) -> list:
    """Ordena lista de artefatos por criticidade (alta > media > baixa).

    Args:
        lista: Lista de artefatos com campo criticidade.

    Returns:
        list: Lista ordenada por prioridade.
    """
    prioridade = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(lista, key=lambda a: prioridade.get(a.get("criticidade", "media"), 1))


@dataclass(frozen=True)
class TestBuilderConfig:
    """Configuração que diferencia os construtores de testes."""

    workspace_agent: str
    agent_label: str
    generation_rules: str
    system_prompt: str


class TestBuilder:
    """Fluxo compartilhado de geração de testes a partir de requisitos."""

    def __init__(self, config: TestBuilderConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(config.agent_label)

    def tests_dir(self) -> Path:
        """Retorna (e cria sob demanda) o diretório de testes do agente."""
        return get_agent_workspace(self.config.workspace_agent)

    def doubt_dir(self) -> Path:
        """Retorna o diretório de artifacts de dúvida do agente."""
        return self.tests_dir() / "doubt_artifacts"

    def receber_requisitos(self, artefatos_json: str) -> dict:
        """Normaliza requisitos e gera os testes correspondentes."""
        try:
            lista = json.loads(artefatos_json)
            if isinstance(lista, dict):
                lista = [lista]
        except json.JSONDecodeError as erro:
            self.logger.warning("[QA] Falha ao ler JSON estrito; tentando fragmentos.")
            try:
                lista = _parse_fragmented_requirements(artefatos_json)
            except Exception:
                caminho = _run_async(
                    self.gerar_doubt_artifact(
                        "ERR_ENTRADA_JSON", f"Erro ao parsear JSON de entrada: {erro}"
                    )
                )
                return {
                    "status": "erro",
                    "mensagem": f"JSON inválido: {erro}",
                    "arquivo_duvida": caminho,
                }

        lista = _normalizar_anexos_inline(lista)
        resultados = _run_async(
            self.processar_todos_em_paralelo(_ordenar_por_criticidade(lista))
        )
        total = len(resultados)
        sucessos = sum(1 for resultado in resultados if resultado["status"] == "sucesso")
        bloqueados = sum(
            1 for resultado in resultados if resultado["status"] == "bloqueado"
        )
        return {
            "status": "concluido",
            "resumo": {
                "total": total,
                "sucessos": sucessos,
                "bloqueados": bloqueados,
                "falhas": total - sucessos - bloqueados,
            },
            "detalhes": resultados,
        }

    async def processar_todos_em_paralelo(
        self, lista_artefatos: list, max_paralelos: int = 5
    ) -> list:
        """Processa requisitos em paralelo, respeitando o limite de concorrência."""
        semaforo = asyncio.Semaphore(max_paralelos)

        async def processar_com_limite(artefato: dict) -> dict:
            async with semaforo:
                return await self.processar_artefato(artefato)

        return await asyncio.gather(
            *(processar_com_limite(artefato) for artefato in lista_artefatos)
        )

    async def processar_artefato(self, artefato: dict) -> dict:
        """Valida um requisito, salva anexos e materializa seu teste pytest."""
        id_artefato = artefato.get("id_artefato", "SEM_ID")
        tipo = artefato.get("tipo", "RF")
        conteudo = artefato.get("conteudo", "")
        modulo = artefato.get("modulo", "geral")
        self.logger.info("[QA] Iniciando: %s (%s)", id_artefato, tipo)

        bloqueio = _validar_artefato(artefato)
        if bloqueio:
            caminho = await self.gerar_doubt_artifact(id_artefato, bloqueio)
            return {
                "id_artefato": id_artefato,
                "status": "bloqueado",
                "motivo": "doubt_artifact_gerado",
                "arquivo_duvida": str(caminho),
                "mensagem": f"Inconsistência: {bloqueio}. Aguardando intervenção humana.",
            }

        try:
            slug = _slugify(id_artefato)
            artefato_dir = self.tests_dir() / slug
            artefato_dir.mkdir(parents=True, exist_ok=True)
            (artefato_dir / "__init__.py").touch(exist_ok=True)
            anexos_salvos = _salvar_arquivos_apoio(artefato, artefato_dir)
            tem_codigo = any(
                path.suffix in [".py", ".java", ".js", ".c"]
                for path in anexos_salvos
            )
            nome_teste = f"test_{slug}.py"
            caminho = artefato_dir / nome_teste
            codigo = self.gerar_pytest_via_llm(
                id_artefato=id_artefato,
                tipo=tipo,
                conteudo=conteudo,
                modulo=modulo,
                arquivos_apoio=anexos_salvos,
                nome_teste=nome_teste,
            )
            caminho.write_text(
                _validar_e_sanitizar_codigo(codigo, id_artefato), encoding="utf-8"
            )
            return {
                "id_artefato": id_artefato,
                "status": "sucesso",
                "fluxo": "A" if tem_codigo else "B",
                "pasta_gerada": str(artefato_dir),
                "arquivo_gerado": str(caminho),
                "arquivos_apoio": [str(path) for path in anexos_salvos],
                "erro": None,
            }
        except Exception as erro:
            self.logger.error("[QA] Erro em %s: %s", id_artefato, erro)
            return {
                "id_artefato": id_artefato,
                "status": "falha",
                "arquivo_gerado": None,
                "erro": str(erro),
            }

    async def gerar_doubt_artifact(self, id_artefato: str, motivo: str) -> str:
        """Registra bloqueios no diretório próprio do construtor."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        diretorio = self.doubt_dir()
        diretorio.mkdir(parents=True, exist_ok=True)
        caminho = diretorio / f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
        caminho.write_text(
            f"""# Doubt Artifact — QA Agent

**ID do Artefato:** {id_artefato}
**Data/Hora:** {timestamp}
**Agente:** {self.config.agent_label}
**Status:** BLOQUEADO — aguardando intervenção humana

---

## Descrição do Bloqueio

{motivo}

## O que é necessário para continuar

[ Preencher após intervenção ]

## Resolução

- **Resolvido por:** [ Preencher ]
- **Data:** [ Preencher ]
- **Ação tomada:** [ Preencher ]
""",
            encoding="utf-8",
        )
        return str(caminho)

    def gerar_pytest_via_llm(
        self,
        id_artefato: str,
        tipo: str,
        conteudo: str,
        modulo: str,
        arquivos_apoio: list[Path],
        nome_teste: str,
    ) -> str:
        """Gera o pytest segundo as regras específicas do construtor."""
        arquivos_textos = []
        for arquivo in arquivos_apoio:
            try:
                arquivos_textos.append(
                    f"--- {arquivo.name} ---\n{arquivo.read_text(encoding='utf-8')}\n"
                )
            except Exception:
                arquivos_textos.append(f"- {arquivo.name} (Arquivo binário ou ilegível)")
        contexto_arquivos = (
            "Arquivos de apoio e CÓDIGO FONTE fornecidos para o teste:\n"
            + "\n".join(arquivos_textos)
            if arquivos_textos
            else "Nenhum arquivo de apoio ou código fonte foi fornecido.\n"
        )
        tem_codigo = any(arquivo.suffix in [".py", ".java", ".js", ".c"] for arquivo in arquivos_apoio)
        instrucao_geracao = (
            "O usuário forneceu o código fonte junto aos requisitos. MAPEAMENTO: "
            "mapeie os cenários de teste contra as funções e métodos reais presentes "
            "no código. Gere os testes pytest COMPLETOS e integrados, utilizando "
            "asserts que validem as lógicas existentes. REGRA DE IMPORTAÇÃO "
            "MANDATÓRIA: faça a importação das funções/classes de forma RELATIVA e "
            "EXPLÍCITA a partir do arquivo fornecido."
            if tem_codigo
            else "Nenhum código fonte foi fornecido — gere em MODO ESQUELETO. Use "
            "@pytest.mark.skip(reason='Aguardando implementação do código fonte') "
            "antes de cada função de teste. O corpo deve ter apenas uma docstring "
            "descrevendo o comportamento esperado. NÃO use 'pass'."
        )
        prompt = f"""Gere SOMENTE código Python válido para {nome_teste}.
Artefato: {id_artefato}
Tipo: {tipo}
Módulo alvo: {modulo}
Requisito: {conteudo}

{contexto_arquivos}

DIRETRIZ DE GERAÇÃO CONDICIONAL:
{instrucao_geracao}

{self.config.generation_rules}
"""
        model_name = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")
        llm_kwargs = {}
        if "/" not in model_name:
            model_name = f"gemini/{model_name}"
            llm_kwargs["api_key"] = os.environ.get("GOOGLE_API_KEY")
        response = completion(
            model=model_name,
            messages=[
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            **llm_kwargs,
        )
        choices = getattr(response, "choices", None)
        codigo = getattr(getattr(choices[0], "message", None), "content", "") if choices else ""
        if not codigo and isinstance(response, dict):
            codigo = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(codigo, str) or not codigo.strip():
            raise ValueError("Modelo retornou conteúdo vazio para geração de pytest.")
        return codigo.strip() + "\n"
