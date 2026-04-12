"""
Tools do Agente Requirements (PRD Optimizer)

Responsabilidades:
- Ler PRDs brutos (de arquivo ou de texto direto)
- Salvar Context Windows em JSON e Markdown
- Gerar Doubt Artifact ao detectar inconsistencias nos requisitos
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationError
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# SCHEMAS DE VALIDACAO (Pydantic)
# -------------------------------------------------------------------

class LeituraPRDSchema(BaseModel):
    caminho: str = Field(..., description="Caminho do arquivo de PRD (.md ou .txt)")

    @field_validator("caminho")
    def validar_caminho(cls, v):
        path = Path(v)
        if not path.is_absolute() and ".." in path.parts:
            raise ValueError("Caminho relativo nao pode conter '..' (path traversal).")
        if path.suffix not in (".md", ".txt"):
            raise ValueError("O PRD deve ser um arquivo .md ou .txt.")
        return v


class PainelLogicoSchema(BaseModel):
    id_painel: str = Field(..., description="Identificador unico do painel, ex: REQ-TACO-AUTH-001")
    modulo: str = Field(..., description="Nome do modulo de origem no PRD")
    titulo: str = Field(..., description="Titulo curto e descritivo do painel")
    descricao: str = Field(..., description="Descricao completa do painel logico fracionado")
    dependencias: list[str] = Field(
        default=[],
        description="IDs de outros paineis dos quais este depende"
    )
    prioridade: str = Field(
        default="media",
        description="Prioridade: alta, media ou baixa"
    )
    estimativa_tokens: int = Field(
        default=0,
        description="Estimativa de tokens necessarios para processar este painel"
    )
    time_responsavel: str = Field(
        default="time4",
        description="Time responsavel pela implementacao deste painel"
    )

    @field_validator("prioridade")
    def validar_prioridade(cls, v):
        if v not in ("alta", "media", "baixa"):
            raise ValueError("Prioridade deve ser alta, media ou baixa.")
        return v

    @field_validator("id_painel")
    def validar_id(cls, v):
        if not v.startswith("REQ-"):
            raise ValueError("O ID do painel deve comecar com REQ- para rastreabilidade.")
        return v


class ContextWindowSchema(BaseModel):
    paineis: list[PainelLogicoSchema] = Field(
        ..., description="Lista de paineis logicos que compoem esta Context Window"
    )
    nome_arquivo_base: str = Field(
        ..., description="Nome base dos arquivos de saida (sem extensao)"
    )
    versao: str = Field(default="1.0.0", description="Versao desta Context Window")

    @field_validator("nome_arquivo_base")
    def validar_nome_base(cls, v):
        path = Path(v)
        if path.is_absolute() or ".." in path.parts or path.suffix:
            raise ValueError(
                "nome_arquivo_base deve ser relativo, sem .. e sem extensao."
            )
        return v


class DoubtArtifactPRDSchema(BaseModel):
    titulo: str = Field(..., description="Titulo curto da inconsistencia encontrada no PRD")
    secao_prd: str = Field(..., description="Secao/modulo do PRD onde a inconsistencia foi detectada")
    descricao: str = Field(..., description="Descricao detalhada do problema encontrado")
    impacto: str = Field(..., description="Qual agente e impactado por essa inconsistencia")
    sugestao: str = Field(
        default="Aguardando esclarecimento e intervencao.",
        description="Sugestao de resolucao"
    )
    nome_arquivo: str = Field(default="Doubt_Artifact_requirements.md")

    @field_validator("nome_arquivo")
    def validar_extensao(cls, v):
        if not v.endswith(".md"):
            raise ValueError("O Doubt Artifact deve ser um arquivo .md.")
        return v


# -------------------------------------------------------------------
# TOOL 1: Ler PRD de Arquivo
# -------------------------------------------------------------------

def tool_ler_prd_arquivo(caminho: str) -> dict:
    """Le o conteudo bruto de um PRD a partir de um arquivo .md ou .txt.

    Args:
        caminho (str): Caminho absoluto ou relativo ao arquivo de PRD.

    Returns:
        dict: Status, conteudo bruto do PRD, numero de linhas e erros.
    """
    try:
        dados = LeituraPRDSchema(caminho=caminho)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "conteudo": None}

    path = Path(dados.caminho)

    if not path.exists():
        return {
            "sucesso": False,
            "erro": "Arquivo nao encontrado: " + caminho,
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
            "erro": "Erro ao ler o arquivo: " + str(e),
            "conteudo": None,
        }


# -------------------------------------------------------------------
# TOOL 2: Salvar Context Window em JSON
# -------------------------------------------------------------------

def tool_salvar_context_window_json(
    paineis: list[dict],
    nome_arquivo_base: str,
    versao: str = "1.0.0",
) -> dict:
    """Salva os paineis logicos fracionados como um arquivo JSON estruturado.

    Args:
        paineis (list): Lista de dicionarios representando os paineis logicos.
        nome_arquivo_base (str): Nome base do arquivo de saida sem extensao.
        versao (str): Versao desta Context Window.

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
        return {"sucesso": False, "erro": "Dados invalidos: " + str(e), "caminho": None}

    payload = {
        "metadata": {
            "versao": dados.versao,
            "gerado_em": datetime.now().isoformat(),
            "gerado_por": "requirements_agent",
            "total_paineis": len(dados.paineis),
            "instrucao_uso": (
                "Este arquivo deve ser lido pelo Agente Coder antes de iniciar "
                "qualquer implementacao. Processe um painel por vez na ordem de prioridade."
            ),
        },
        "paineis": [p.model_dump() for p in dados.paineis],
    }

    path = Path(dados.nome_arquivo_base + ".json")
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
        return {"sucesso": False, "erro": "Erro ao salvar JSON: " + str(e), "caminho": None}


# -------------------------------------------------------------------
# TOOL 3: Salvar Context Window em Markdown
# -------------------------------------------------------------------

def tool_salvar_context_window_markdown(
    paineis: list[dict],
    nome_arquivo_base: str,
    versao: str = "1.0.0",
) -> dict:
    """Salva os paineis logicos fracionados como um arquivo Markdown legivel por humanos.

    Args:
        paineis (list): Lista de dicionarios representando os paineis logicos.
        nome_arquivo_base (str): Nome base do arquivo de saida sem extensao.
        versao (str): Versao desta Context Window.

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
        return {"sucesso": False, "erro": "Dados invalidos: " + str(e), "caminho": None}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linhas = [
        "# Context Window",
        "",
        "**Versao:** " + dados.versao,
        "**Gerado em:** " + timestamp,
        "**Gerado por:** requirements_agent",
        "**Total de paineis:** " + str(len(dados.paineis)),
        "",
        "> Instrucao de uso: processar um painel por vez na ordem de prioridade.",
        "> Validar este documento antes de enviar ao Agente Coder.",
        "",
        "---",
        "",
    ]

    prioridades = {"alta": [], "media": [], "baixa": []}
    for p in dados.paineis:
        prioridades[p.prioridade].append(p)

    icones = {"alta": "ALTA", "media": "MEDIA", "baixa": "BAIXA"}

    for nivel, grupo in prioridades.items():
        if not grupo:
            continue
        linhas.append("## Paineis de Prioridade " + icones[nivel])
        linhas.append("")

        for painel in grupo:
            deps = ", ".join(painel.dependencias) if painel.dependencias else "Nenhuma"
            linhas += [
                "### " + painel.id_painel + " — " + painel.titulo,
                "",
                "| Campo | Valor |",
                "|-------|-------|",
                "| Modulo de origem | " + painel.modulo + " |",
                "| Dependencias | " + deps + " |",
                "| Estimativa de tokens | ~" + str(painel.estimativa_tokens) + " tokens |",
                "",
                "**Descricao:**",
                painel.descricao,
                "",
                "---",
                "",
            ]

    linhas += [
        "## Checklist de Validacao",
        "",
        "- [ ] Todos os paineis foram revisados",
        "- [ ] Dependencias entre paineis estao corretas",
        "- [ ] Estimativas de tokens estao dentro do limite aceitavel",
        "- [ ] Arquivo JSON correspondente foi gerado",
        "- [ ] Resultado validado antes do envio ao Coder",
        "",
    ]

    conteudo = "\n".join(linhas)
    path = Path(dados.nome_arquivo_base + ".md")

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
        return {"sucesso": False, "erro": "Erro ao salvar Markdown: " + str(e), "caminho": None}


# -------------------------------------------------------------------
# TOOL 4: Gerar Doubt Artifact
# -------------------------------------------------------------------

def tool_gerar_doubt_artifact_prd(
    titulo: str,
    secao_prd: str,
    descricao: str,
    impacto: str,
    sugestao: str = "Aguardando esclarecimento e intervencao.",
    nome_arquivo: str = "Doubt_Artifact_requirements.md",
) -> dict:
    """Gera um Doubt Artifact ao detectar inconsistencias, ambiguidades ou lacunas no PRD.

    ATENCAO: use esta tool sempre que encontrar requisitos contraditorios ou ambiguidades
    que impecam o fracionamento seguro. A execucao deve ser PAUSADA apos gerar este arquivo.

    Args:
        titulo (str): Titulo curto da inconsistencia.
        secao_prd (str): Secao ou modulo do PRD onde o problema foi encontrado.
        descricao (str): Descricao detalhada do problema.
        impacto (str): Qual componente do sistema e impactado.
        sugestao (str): Sugestao de resolucao ou proximo passo.
        nome_arquivo (str): Nome do arquivo de saida (padrao: Doubt_Artifact_PRD.md).

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

    conteudo = (
        "# Doubt Artifact — " + dados.titulo + "\n"
        "\n"
        "> EXECUCAO PAUSADA — INTERVENCAO HUMANA NECESSARIA\n"
        "> Gerado pelo requirements_agent (TACO IDE) em " + timestamp + "\n"
        "\n"
        "---\n"
        "\n"
        "## Localizacao no PRD\n"
        "Secao / Modulo afetado: " + dados.secao_prd + "\n"
        "\n"
        "## Descricao do Problema\n"
        + dados.descricao + "\n"
        "\n"
        "## Impacto\n"
        + dados.impacto + "\n"
        "\n"
        "## Sugestao de Resolucao\n"
        + dados.sugestao + "\n"
        "\n"
        "---\n"
        "\n"
        "## Checklist de Resolucao\n"
        "- [ ] Notificacao sobre a inconsistencia enviada\n"
        "- [ ] Decisao tomada e documentada\n"
        "- [ ] PRD atualizado com a correcao\n"
        "- [ ] Agente pode retomar o fracionamento\n"
        "\n"
        "Responsavel: Lider Operacional\n"
        "Status: Pendente\n"
    )

    path = Path(dados.nome_arquivo)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        logger.warning("[DOUBT ARTIFACT PRD] " + dados.titulo + " — secao: " + dados.secao_prd)
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "titulo": dados.titulo,
            "status": "EXECUCAO PAUSADA — aguardando intervencao humana",
        }
    except Exception as e:
        return {"sucesso": False, "erro": "Erro ao salvar Doubt Artifact: " + str(e), "caminho": None}


# -------------------------------------------------------------------
# EXPORTANDO TOOLS PARA O ADK
# -------------------------------------------------------------------

tool_ler_prd_arquivo_adk = FunctionTool(tool_ler_prd_arquivo)
tool_salvar_context_window_json_adk = FunctionTool(tool_salvar_context_window_json)
tool_salvar_context_window_markdown_adk = FunctionTool(tool_salvar_context_window_markdown)
tool_gerar_doubt_artifact_prd_adk = FunctionTool(tool_gerar_doubt_artifact_prd)
