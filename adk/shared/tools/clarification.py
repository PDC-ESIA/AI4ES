"""Ferramenta de clarificação genérica para agentes de Engenharia de Software."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

class ClarificationSchema(BaseModel):
    titulo: str = Field(..., description="Título curto da inconsistencia ou dúvida encontrada")
    secao: str = Field(..., description="Seção, módulo ou componente onde a dúvida foi detectada")
    descricao: str = Field(..., description="Descrição detalhada do problema ou falta de contexto")
    impacto: str = Field(..., description="Qual o impacto dessa dúvida no andamento da tarefa")
    sugestao: str = Field(
        default="Aguardando esclarecimento e intervenção do usuário.",
        description="Sugestão de resolução ou pergunta direta ao usuário"
    )
    nome_arquivo: str = Field(default="Doubt_Artifact_Clarification.md")

    @field_validator("nome_arquivo")
    @classmethod
    def validar_extensao(cls, v: str) -> str:
        if not v.endswith(".md"):
            raise ValueError("O Doubt Artifact deve ser um arquivo .md.")
        return v

def tool_ask_clarification(
    titulo: str,
    secao: str,
    descricao: str,
    impacto: str,
    sugestao: str = "Aguardando esclarecimento e intervenção do usuário.",
    nome_arquivo: str = "Doubt_Artifact_Clarification.md",
    base_dir: Optional[str] = None,
) -> dict:
    """Gera um Doubt Artifact e pausa a execução solicitando esclarecimento ao supervisor.

    Use sempre que encontrar requisitos contraditórios, ambiguidades
    graves, falta de contexto crítico ou qualquer impeditivo objetivo
    para continuar a tarefa. A tool grava um arquivo Markdown estruturado
    documentando o problema, com cabeçalho "EXECUÇÃO PAUSADA — INTERVENÇÃO
    NECESSÁRIA" e checklist para o supervisor responder.

    Após chamar esta capacidade, o agente DEVE interromper o trabalho
    e devolver controle ao supervisor — não tente "adivinhar" uma
    resolução para a dúvida registrada.

    Args:
        titulo: Título curto da inconsistência ou dúvida encontrada.
        secao: Seção, módulo ou componente onde a dúvida foi detectada.
        descricao: Descrição detalhada do problema ou da falta de
            contexto.
        impacto: O impacto da dúvida no andamento da tarefa.
        sugestao: Pergunta direta ou sugestão de resolução ao supervisor.
            Default "Aguardando esclarecimento e intervenção do usuário."
        nome_arquivo: Nome do arquivo de saída. Default
            "Doubt_Artifact_Clarification.md". Obrigatório terminar em
            .md.
        base_dir: Diretório onde o artefato será salvo. Quando None
            (default), grava relativo ao CWD do processo — comportamento
            legado. Quando o agent_factory cria o agente via
            create_se_agent(agent_subdir=...), injeta automaticamente
            base_dir=workspace do agente, isolando o artefato em
            workspace_output/<subdir>/.

    Returns:
        dict com chaves: `sucesso` (bool), `erro` (str ou None),
        `caminho` (path absoluto do artefato em sucesso, None em falha),
        `título` (str em sucesso), `status` (str descritivo, em sucesso
        contém "EXECUÇÃO INTERROMPIDA").
    """
    try:
        dados = ClarificationSchema(
            titulo=titulo,
            secao=secao,
            descricao=descricao,
            impacto=impacto,
            sugestao=sugestao,
            nome_arquivo=nome_arquivo,
        )
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conteudo = f"""# Doubt Artifact — {dados.titulo}

> EXECUÇÃO PAUSADA — INTERVENÇÃO NECESSÁRIA
> Gerado em {timestamp}

---

## Localização / Contexto
{dados.secao}

## Descrição do Problema / Dúvida
{dados.descricao}

## Impacto
{dados.impacto}

## Pergunta / Sugestão de Resolução
{dados.sugestao}

---

## Checklist de Resolução
- [ ] Dúvida respondida pelo usuário
- [ ] Contexto atualizado
- [ ] Agente pode retomar a execução

Status: Pendente
"""

    diretorio = Path(base_dir) if base_dir is not None else Path(".")
    diretorio.mkdir(parents=True, exist_ok=True)
    path = diretorio / dados.nome_arquivo
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        logger.warning(f"[CLARIFICATION REQUIRED] {dados.titulo} — secao: {dados.secao}")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(path.resolve()),
            "título": dados.titulo,
            "status": "EXECUÇÃO INTERROMPIDA — aguardando resposta do usuário.",
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao salvar Clarification Artifact: {e}",
            "caminho": None,
        }

tool_ask_clarification_adk = FunctionTool(tool_ask_clarification)
