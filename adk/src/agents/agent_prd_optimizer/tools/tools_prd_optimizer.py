"""
Tools do Agente PRD Optimizer

Responsabilidades:
- Ler PRDs brutos (de arquivo ou de texto direto)
- Salvar Context Windows em JSON e Markdown
- Gerar Doubt Artifact ao detectar inconsistências nos requisitos
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# SCHEMAS DE VALIDAÇÃO (Pydantic)
# -------------------------------------------------------------------

class LeituraPRDSchema(BaseModel):
    caminho: str = Field(..., description="Caminho do arquivo de PRD (.md ou .txt)")

    @field_validator("caminho")
    def validar_caminho(cls, v):
        path = Path(v)
        if not path.is_absolute() and ".." in path.parts:
            raise ValueError("Caminho relativo não pode conter '..' (path traversal).")
        if path.suffix not in (".md", ".txt"):
            raise ValueError("O PRD deve ser um arquivo .md ou .txt.")
        return v


class PainelLogicoSchema(BaseModel):
    id_painel: str = Field(..., description="Identificador único do painel, ex: 'REQ-TACO-AUTH-001'")
    modulo: str = Field(..., description="Nome do módulo de origem no PRD")
    titulo: str = Field(..., description="Título curto e descritivo do painel")
    descricao: str = Field(..., description="Descrição completa do painel lógico fracionado")
    dependencias: list[str] = Field(
        default=[],
        description="IDs de outros painéis dos quais este depende"
    )
    prioridade: str = Field(
        default="media",
        description="Prioridade: 'alta', 'media' ou 'baixa'"
    )
    estimativa_tokens: int = Field(
        default=0,
        description="Estimativa de tokens necessários para processar este painel"
    )
    time_responsavel: str = Field(
        default="time4",
        description="Time responsável pela implementação deste painel"
    )

    @field_validator("prioridade")
    def validar_prioridade(cls, v):
        if v not in ("alta", "media", "baixa"):
            raise ValueError("Prioridade deve ser 'alta', 'media' ou 'baixa'.")
        return v

    @field_validator("id_painel")
    def validar_id(cls, v):
        if not v.startswith("REQ-"):
            raise ValueError("O ID do painel deve começar com 'REQ-' para rastreabilidade.")
        return v


class ContextWindowSchema(BaseModel):
    paineis: list[PainelLogicoSchema] = Field(
        ..., description="Lista de painéis lógicos que compõem esta Context Window"
    )
    nome_arquivo_base: str = Field(
        ..., description="Nome base dos arquivos de saída (sem extensão)"
    )
    versao: str = Field(default="1.0.0", description="Versão desta Context Window")

    @field_validator("nome_arquivo_base")
    def validar_nome_base(cls, v):
        path = Path(v)
        if path.is_absolute() or ".." in path.parts or path.suffix:
            raise ValueError(
                "nome_arquivo_base deve ser relativo, sem '..' e sem extensão."
            )
        return v


class DoubtArtifactPRDSchema(BaseModel):
    titulo: str = Field(..., description="Título curto da inconsistência encontrada no PRD")
    secao_prd: str = Field(..., description="Seção/módulo do PRD onde a inconsistência foi detectada")
    descricao: str = Field(..., description="Descrição detalhada do problema encontrado")
    impacto: str = Field(..., description="Qual agente é impactado por essa inconsistência")
    sugestao: str = Field(
        default="Aguardando esclarecimento e intervenção.",
        description="Sugestão de resolução"
    )
    nome_arquivo: str = Field(default="Doubt_Artifact_PRD.md")

    @field_validator("nome_arquivo")
    def validar_extensao(cls, v):
        if not v.endswith(".md"):
            raise ValueError("O Doubt Artifact deve ser um arquivo .md.")
        return v


# -------------------------------------------------------------------
# TOOL 1: Ler PRD de Arquivo
# -------------------------------------------------------------------

def tool_ler_prd_arquivo(caminho: str) -> dict:
    """Lê o conteúdo bruto de um PRD a partir de um arquivo .md ou .txt.

    Args:
        caminho (str): Caminho absoluto ou relativo ao arquivo de PRD.

    Returns:
        dict: Status, conteúdo bruto do PRD, número de linhas e erros.
    """
    try:
        dados = LeituraPRDSchema(caminho=caminho)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "conteudo": None}

    path = Path(dados.caminho)

    if not path.exists():
        return {
            "sucesso": False,
            "erro": f"Arquivo não encontrado: '{caminho}'.",
            "conteudo": None,
        }

    try:
        conteudo = path.read_text(encoding="utf-8")
        return {
            "sucesso": True,
            "erro": None,
            "conteudo": conteudo,
            "total_linhas": len(conteudo.splitlines()),
            "total_caracteres": len(conteudo),
            "caminho_absoluto": str(path.resolve()),
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao ler o arquivo: {e}",
            "conteudo": None,
        }


# -------------------------------------------------------------------
# TOOL 2: Salvar Context Window em JSON
# -------------------------------------------------------------------

def tool_salvar_context_window_json(
    paineis: list,
    nome_arquivo_base: str,
    versao: str = "1.0.0",
) -> dict:
    """Salva os painéis lógicos fracionados como um arquivo JSON estruturado.

    O JSON gerado é o formato de metadados que alimentará o Agente Coder MVP,
    garantindo que ele receba apenas o contexto necessário para cada tarefa.

    Args:
        paineis (list): Lista de dicionários representando os painéis lógicos.
                        Cada painel deve ter: id_painel, modulo, titulo, descricao,
                        dependencias, prioridade, estimativa_tokens, time_responsavel.
        nome_arquivo_base (str): Nome base do arquivo de saída (sem extensão).
                                 Ex: 'context_windows/cw_auth_v1'
        versao (str): Versão desta Context Window (padrão: '1.0.0').

    Returns:
        dict: Status, caminho do arquivo JSON gerado e erros.
    """
    try:
        paineis_validados = [PainelLogicoSchema(**p) for p in paineis]
        dados = ContextWindowSchema(
            paineis=paineis_validados,
            nome_arquivo_base=nome_arquivo_base,
            versao=versao,
        )
    except (ValidationError, TypeError) as e:
        return {"sucesso": False, "erro": f"Dados inválidos: {e}", "caminho": None}

    payload = {
        "metadata": {
            "versao": dados.versao,
            "gerado_em": datetime.now().isoformat(),
            "gerado_por": "prd_optimizer_agent",
            "projeto": "TACO IDE",
            "total_paineis": len(dados.paineis),
            "instrucao_uso": (
                "Este arquivo deve ser lido pelo Agente Coder MVP antes de iniciar "
                "qualquer implementação. Processe um painel por vez na ordem de prioridade."
            ),
        },
        "paineis": [p.model_dump() for p in dados.paineis],
    }

    path = Path(f"{dados.nome_arquivo_base}.json")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "total_paineis": len(dados.paineis),
            "versao": dados.versao,
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar JSON: {e}", "caminho": None}


# -------------------------------------------------------------------
# TOOL 3: Salvar Context Window em Markdown
# -------------------------------------------------------------------

def tool_salvar_context_window_markdown(
    paineis: list,
    nome_arquivo_base: str,
    versao: str = "1.0.0",
) -> dict:
    """Salva os painéis lógicos fracionados como um arquivo Markdown legível por humanos.

    O Markdown gerado é o formato de revisão humana.

    Args:
        paineis (list): Lista de dicionários representando os painéis lógicos.
                        Mesma estrutura exigida pela tool de JSON.
        nome_arquivo_base (str): Nome base do arquivo de saída (sem extensão).
                                 Ex: 'context_windows/cw_auth_v1'
        versao (str): Versão desta Context Window (padrão: '1.0.0').

    Returns:
        dict: Status, caminho do arquivo Markdown gerado e erros.
    """
    try:
        paineis_validados = [PainelLogicoSchema(**p) for p in paineis]
        dados = ContextWindowSchema(
            paineis=paineis_validados,
            nome_arquivo_base=nome_arquivo_base,
            versao=versao,
        )
    except (ValidationError, TypeError) as e:
        return {"sucesso": False, "erro": f"Dados inválidos: {e}", "caminho": None}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linhas = [
        f"# Context Window",
        f"",
        f"**Versão:** `{dados.versao}`  ",
        f"**Gerado em:** `{timestamp}`  ",
        f"**Gerado por:** Agente PRD Optimizer",
        f"**Total de painéis:** {len(dados.paineis)}  ",
        f"",
        f"> **Instrução de uso:** Este documento deve ser processado pelo Agente Coder MVP",
        f"> **um painel por vez**, na ordem de prioridade indicada.",
        f"",
        f"---",
        f"",
    ]

    # Agrupar por prioridade
    prioridades = {"alta": [], "media": [], "baixa": []}
    for p in dados.paineis:
        prioridades[p.prioridade].append(p)

    icones = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}

    for nivel, grupo in prioridades.items():
        if not grupo:
            continue
        linhas.append(f"## {icones[nivel]} Painéis de Prioridade {nivel.upper()}")
        linhas.append("")

        for painel in grupo:
            deps = ", ".join(painel.dependencias) if painel.dependencias else "Nenhuma"
            linhas += [
                f"### `{painel.id_painel}` — {painel.titulo}",
                f"",
                f"| Campo | Valor |",
                f"|-------|-------|",
                f"| **Módulo de origem** | {painel.modulo} |",
                f"| **Time responsável** | `{painel.time_responsavel}` |",
                f"| **Dependências** | {deps} |",
                f"| **Estimativa de tokens** | ~{painel.estimativa_tokens} tokens |",
                f"",
                f"**Descrição:**",
                f"{painel.descricao}",
                f"",
                f"---",
                f"",
            ]

    linhas += [
        f"## Checklist de Validação",
        f"",
        f"- [ ] Todos os painéis foram revisados",
        f"- [ ] Dependências entre painéis estão corretas",
        f"- [ ] Estimativas de tokens estão dentro do limite aceitável",
        f"- [ ] Arquivo JSON correspondente foi gerado",
        f"- [ ] Resultado validado antes do envio ao Coder",
        f"",
    ]

    conteudo = "\n".join(linhas)
    path = Path(f"{dados.nome_arquivo_base}.md")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "total_paineis": len(dados.paineis),
            "versao": dados.versao,
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar Markdown: {e}", "caminho": None}


# -------------------------------------------------------------------
# TOOL 4: Gerar Doubt Artifact (específico para inconsistências em PRDs)
# -------------------------------------------------------------------

def tool_gerar_doubt_artifact_prd(
    titulo: str,
    secao_prd: str,
    descricao: str,
    impacto: str,
    sugestao: str = "Aguardando esclarecimento e intervenção.",
    nome_arquivo: str = "Doubt_Artifact_PRD.md",
) -> dict:
    """Gera um Doubt Artifact ao detectar inconsistências, ambiguidades ou lacunas no PRD.

    ATENÇÃO: use esta tool sempre que encontrar requisitos contraditórios, seções
    incompletas ou ambiguidades que impeçam o fracionamento seguro. A execução do
    agente deve ser PAUSADA após gerar este arquivo.

    Args:
        titulo (str): Título curto da inconsistência.
        secao_prd (str): Seção ou módulo do PRD onde o problema foi encontrado.
        descricao (str): Descrição detalhada do problema.
        impacto (str): Qual componente do sistema é impactado.
        sugestao (str): Sugestão de resolução ou próximo passo.
        nome_arquivo (str): Nome do arquivo de saída (padrão: Doubt_Artifact_PRD.md).

    Returns:
        dict: Status, caminho do arquivo gerado e mensagem de pausa.
    """
    try:
        dados = DoubtArtifactPRDSchema(
            titulo=titulo,
            secao_prd=secao_prd,
            descricao=descricao,
            impacto=impacto,
            sugestao=sugestao,
            nome_arquivo=nome_arquivo,
        )
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conteudo = f"""# Doubt Artifact — {dados.titulo}

> **⚠️ EXECUÇÃO PAUSADA — INTERVENÇÃO HUMANA NECESSÁRIA**
> Gerado pelo Agente PRD Optimizer em `{timestamp}`

---

## Localização no PRD
**Seção / Módulo afetado:** `{dados.secao_prd}`

## Descrição do Problema
{dados.descricao}

## Impacto
{dados.impacto}

## Sugestão de Resolução
{dados.sugestao}

---

## Checklist de Resolução
- [ ] Notificação sobre a inconsistência
- [ ] Decisão tomada e documentada
- [ ] PRD atualizado com a correção
- [ ] Agente PRD Optimizer pode retomar o fracionamento

**Responsável:** Líder Operacional
**Status:** 🔴 Pendente
"""

    path = Path(dados.nome_arquivo)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        logger.warning(
            f"[DOUBT ARTIFACT PRD] '{dados.titulo}' — seção: {dados.secao_prd}"
        )
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "titulo": dados.titulo,
            "status": "EXECUÇÃO PAUSADA — aguardando intervenção humana",
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar Doubt Artifact: {e}", "caminho": None}


# -------------------------------------------------------------------
# EXPORTANDO TOOLS PARA O ADK
# -------------------------------------------------------------------

tool_ler_prd_arquivo_adk = FunctionTool(tool_ler_prd_arquivo)
tool_salvar_context_window_json_adk = FunctionTool(tool_salvar_context_window_json)
tool_salvar_context_window_markdown_adk = FunctionTool(tool_salvar_context_window_markdown)
tool_gerar_doubt_artifact_prd_adk = FunctionTool(tool_gerar_doubt_artifact_prd)