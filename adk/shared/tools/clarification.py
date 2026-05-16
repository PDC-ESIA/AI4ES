"""Ferramenta de clarificação genérica para agentes de Engenharia de Software."""

import logging
from datetime import datetime
from pathlib import Path

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
) -> dict:
    """Gera um Doubt Artifact ao detectar inconsistencias, ambiguidades ou falta de contexto.

    ATENÇÃO: use esta tool SEMPRE que encontrar requisitos contraditórios,
    ambiguidades, falta de código ou qualquer impeditivo para continuar seu trabalho.
    A execução deve ser PAUSADA após gerar este arquivo.
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

    path = Path(dados.nome_arquivo)
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
