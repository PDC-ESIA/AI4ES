"""
Servidor de teste local — simula o Agente Supervisor enviando artefatos ao QA Agent.
O fluxo passa pelo Runner do ADK, exercitando o agente de verdade.

Como rodar:
    cd adk/
    uvicorn src.agents.qa_agent.server_test:app --reload --port 8000

Documentação interativa:
    http://localhost:8000/docs
"""

import json
import uuid

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import qa_agent

load_dotenv(override=True)  # Carrega variáveis de ambiente do .env, sobrescrevendo se necessário

app = FastAPI(
    title="QA Agent — Simulador do Supervisor",
    description="Endpoint HTTP para testar o QA Agent via Runner do ADK.",
    version="0.1.0",
)

# ──────────────────────────────────────────────────────────────────────────────
# Runner do ADK
# ──────────────────────────────────────────────────────────────────────────────

session_service = InMemorySessionService()

runner = Runner(
    agent=qa_agent,
    app_name="qa_agent_server_test",
    session_service=session_service,
)


async def _executar_agente(mensagem: str) -> str:
    """Cria uma sessão isolada e executa o agente via Runner."""
    session_id = str(uuid.uuid4())
    user_id = "supervisor_simulado"

    await session_service.create_session(
        app_name="qa_agent_server_test",
        user_id=user_id,
        session_id=session_id,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=mensagem)],
    )

    resposta_final = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    resposta_final += part.text

    return resposta_final


# ──────────────────────────────────────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────────────────────────────────────

class Artefato(BaseModel):
    id_artefato: str
    tipo: str
    conteudo: str
    modulo: str = "geral"
    criticidade: str = "media"

    model_config = {
        "json_schema_extra": {
            "example": {
                "id_artefato": "RF-001",
                "tipo": "RF",
                "conteudo": "O sistema deve permitir login com e-mail e senha.",
                "modulo": "autenticacao",
                "criticidade": "alta",
            }
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "agente": "qa_agent"}


@app.post("/requisito")
async def enviar_requisito(artefato: Artefato):
    """Simula o Supervisor enviando UM artefato ao QA Agent via Runner do ADK."""
    mensagem = (
        f"Gere testes para o seguinte artefato de requisito:\n"
        f"{json.dumps([artefato.model_dump()], ensure_ascii=False, indent=2)}"
    )
    resposta = await _executar_agente(mensagem)
    return {"agente": "qa_agent", "resposta": resposta}


@app.post("/requisitos")
async def enviar_requisitos(artefatos: list[Artefato]):
    """Simula o Supervisor enviando MÚLTIPLOS artefatos ao QA Agent via Runner do ADK."""
    payload = [a.model_dump() for a in artefatos]
    mensagem = (
        f"Gere testes para os seguintes artefatos de requisito:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    resposta = await _executar_agente(mensagem)
    return {"agente": "qa_agent", "resposta": resposta}