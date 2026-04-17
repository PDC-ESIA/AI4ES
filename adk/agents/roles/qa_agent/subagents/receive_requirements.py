import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from litellm import completion

logger = logging.getLogger("qa_agent")

# Caminhos base — relativos à raiz do agente
_BASE_DIR = Path(__file__).parent.parent
TESTS_DIR = _BASE_DIR / "artefactsTests"
DOUBT_DIR = _BASE_DIR / "doubt_artifacts"

# ──────────────────────────────────────────────────────────────────────────────
# Ponto de entrada público (registrado como FunctionTool no agent.py)
# ──────────────────────────────────────────────────────────────────────────────

def _run_async(coro):
    """
    Executa uma coroutine de forma segura independente de haver
    um event loop rodando ou não (compatível com FastAPI + ADK).
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


def receber_requisitos(artefatos_json: str) -> dict:
    """
    Recebe uma lista de artefatos de requisito em JSON e gera testes pytest
    em paralelo para cada um.

    Args:
        artefatos_json: String JSON com um ou mais artefatos.
            Formato de um artefato:
            {
                "id_artefato": "RF-001",
                "tipo": "RF",
                "conteudo": "O sistema deve...",
                "modulo": "nome_do_modulo",
                "criticidade": "alta"
            }

    Returns:
        Relatório consolidado:
        {
            "status": "concluido",
            "resumo": { "total": N, "sucessos": N, "bloqueados": N, "falhas": N },
            "detalhes": [ ... ]
        }
    """
    try:
        lista = json.loads(artefatos_json)
        if isinstance(lista, dict):
            lista = [lista]
    except json.JSONDecodeError as e:
        logger.error(f"[QA] JSON inválido: {e}")
        caminho = _run_async(
            _gerar_doubt_artifact("ERR_ENTRADA_JSON", f"Erro ao parsear JSON de entrada: {e}")
        )
        return {
            "status": "erro",
            "mensagem": f"JSON inválido: {e}",
            "arquivo_duvida": caminho,
        }

    lista = _ordenar_por_criticidade(lista)
    resultados = _run_async(_processar_todos_em_paralelo(lista))

    total     = len(resultados)
    sucessos  = sum(1 for r in resultados if r["status"] == "sucesso")
    bloqueados = sum(1 for r in resultados if r["status"] == "bloqueado")
    falhas    = total - sucessos - bloqueados

    return {
        "status": "concluido",
        "resumo": {
            "total": total,
            "sucessos": sucessos,
            "bloqueados": bloqueados,
            "falhas": falhas,
        },
        "detalhes": resultados,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Processamento paralelo
# ──────────────────────────────────────────────────────────────────────────────

async def _processar_todos_em_paralelo(
    lista_artefatos: list,
    max_paralelos: int = 5,
) -> list:
    semaforo = asyncio.Semaphore(max_paralelos)

    async def processar_com_limite(artefato):
        async with semaforo:
            return await _processar_artefato(artefato)

    return await asyncio.gather(*[processar_com_limite(a) for a in lista_artefatos])


async def _processar_artefato(artefato: dict) -> dict:
    id_artefato = artefato.get("id_artefato", "SEM_ID")
    tipo        = artefato.get("tipo", "RF")
    conteudo    = artefato.get("conteudo", "")
    modulo      = artefato.get("modulo", "geral")

    logger.info(f"[QA] Iniciando: {id_artefato} ({tipo})")

    # Valida antes de gerar
    bloqueio = _validar_artefato(artefato)
    if bloqueio:
        caminho = await _gerar_doubt_artifact(id_artefato, bloqueio)
        logger.warning(f"[QA] Bloqueado: {id_artefato} → {caminho}")
        return {
            "id_artefato": id_artefato,
            "status": "bloqueado",
            "motivo": "doubt_artifact_gerado",
            "arquivo_duvida": str(caminho),
            "mensagem": f"Inconsistência: {bloqueio}. Aguardando intervenção humana.",
        }

    try:
        slug = _slugify(id_artefato)
        artefato_dir = TESTS_DIR / slug
        artefato_dir.mkdir(parents=True, exist_ok=True)

        anexos_salvos = _salvar_arquivos_apoio(artefato, artefato_dir)

        nome_teste = f"test_{slug}.py"
        caminho = artefato_dir / nome_teste

        codigo = _gerar_pytest_via_llm(
            id_artefato=id_artefato,
            tipo=tipo,
            conteudo=conteudo,
            modulo=modulo,
            arquivos_apoio=anexos_salvos,
            nome_teste=nome_teste,
        )
        caminho.write_text(codigo, encoding="utf-8")

        logger.info(f"[QA] Concluído: {id_artefato} → {caminho}")
        return {
            "id_artefato": id_artefato,
            "status": "sucesso",
            "pasta_gerada": str(artefato_dir),
            "arquivo_gerado": str(caminho),
            "arquivos_apoio": [str(p) for p in anexos_salvos],
            "erro": None,
        }

    except Exception as e:
        logger.error(f"[QA] Erro em {id_artefato}: {e}")
        return {
            "id_artefato": id_artefato,
            "status": "falha",
            "arquivo_gerado": None,
            "erro": str(e),
        }


# ──────────────────────────────────────────────────────────────────────────────
# Validação
# ──────────────────────────────────────────────────────────────────────────────

def _validar_artefato(artefato: dict) -> str | None:
    """Retorna descrição do bloqueio ou None se o artefato estiver ok."""
    if not artefato.get("conteudo", "").strip():
        return "Campo 'conteudo' vazio — impossível gerar testes sem descrição do requisito."
    if not artefato.get("modulo", "").strip():
        return "Campo 'modulo' vazio — impossível identificar o código a ser testado."
    if artefato.get("tipo") not in ("RF", "HU", "UC", "RNF", "RN"):
        return (
            f"Tipo desconhecido: '{artefato.get('tipo')}'. "
            "Esperado: RF, HU, UC, RNF ou RN."
        )
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Doubt Artifact
# ──────────────────────────────────────────────────────────────────────────────

async def _gerar_doubt_artifact(id_artefato: str, motivo: str) -> str:
    """Gera Doubt_Artifact.md e retorna o caminho do arquivo criado."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    DOUBT_DIR.mkdir(parents=True, exist_ok=True)

    nome = f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
    caminho = DOUBT_DIR / nome

    conteudo = f"""# Doubt Artifact — QA Agent

**ID do Artefato:** {id_artefato}
**Data/Hora:** {timestamp}
**Agente:** qa_agent
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
"""
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)


# ──────────────────────────────────────────────────────────────────────────────
# Geração do template pytest
# ──────────────────────────────────────────────────────────────────────────────

def _slugify(texto: str) -> str:
    base = (texto or "artefato").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = base.strip("_")
    return base or "artefato"


def _safe_filename(nome: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", (nome or "arquivo.txt").strip())
    cleaned = cleaned.lstrip(".")
    return cleaned or "arquivo.txt"


def _salvar_arquivos_apoio(artefato: dict, destino: Path) -> list[Path]:
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


def _gerar_pytest_via_llm(
    id_artefato: str,
    tipo: str,
    conteudo: str,
    modulo: str,
    arquivos_apoio: list[Path],
    nome_teste: str,
) -> str:
    model_name = os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")
    arquivos_desc = "\n".join([f"- {p.name}" for p in arquivos_apoio])
    contexto_arquivos = (
        "Arquivos de apoio salvos na mesma pasta do teste:\n"
        f"{arquivos_desc}\n"
        if arquivos_desc
        else "Nenhum arquivo de apoio foi fornecido.\n"
    )
    prompt = f"""Gere SOMENTE código Python válido para {nome_teste}.
Artefato: {id_artefato}
Tipo: {tipo}
Módulo alvo: {modulo}
Requisito:
{conteudo}

{contexto_arquivos}
Regras obrigatórias:
- Retorne apenas código Python, sem markdown.
- Use pytest.
- O teste deve ser executável mesmo sem instalação de módulos externos ao diretório local.
- Se houver arquivo-fonte local, faça import relativo via pathlib/sys.path usando a própria pasta do teste.
- Se não houver código-fonte importável, gere testes de contrato (validações e comportamentos inferíveis) sem import quebrado.
- Cubra cenários feliz, inválido e borda.
- Inclua asserts objetivos.
- Não use placeholders TODO, não use pass vazio, não deixe testes sem lógica.
"""

    response = completion(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "Você gera exclusivamente código de teste pytest executável.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    codigo = ""
    choices = getattr(response, "choices", None)
    if choices and len(choices) > 0:
        message = getattr(choices[0], "message", None)
        codigo = getattr(message, "content", "") if message else ""

    if not codigo and isinstance(response, dict):
        response_choices = response.get("choices", [])
        if response_choices:
            codigo = response_choices[0].get("message", {}).get("content", "")

    if not isinstance(codigo, str) or not codigo.strip():
        raise ValueError("Modelo retornou conteúdo vazio para geração de pytest.")

    return codigo.strip() + "\n"


# ──────────────────────────────────────────────────────────────────────────────
# Priorização
# ──────────────────────────────────────────────────────────────────────────────

def _ordenar_por_criticidade(lista: list) -> list:
    prioridade = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(lista, key=lambda a: prioridade.get(a.get("criticidade", "media"), 1))


agent = LlmAgent(
    name="receber_requisitos",
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")),
    description=(
        "Subagente que recebe artefatos de requisito em JSON e gera arquivos pytest "
        "funcionais em artefactsTests."
    ),
    instruction=(
        "Você deve sempre chamar a tool receber_requisitos com o JSON recebido, "
        "sem alterar o payload. Retorne o resultado da tool ao final."
    ),
    tools=[
        FunctionTool(receber_requisitos),
    ],
)
