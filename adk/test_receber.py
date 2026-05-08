import asyncio
import json
import base64
from agents.roles.qa_agent.subagents.receive_requirements import receber_requisitos

payload = [{
    "id_artefato": "TEST-01",
    "tipo": "RF",
    "conteudo": "Teste",
    "parts": [{
        "inlineData": {
            "displayName": "calculadora.py",
            "mimeType": "text/x-python",
            "data": base64.b64encode(b"def teste(): pass").decode('utf-8')
        }
    }]
}]

print(receber_requisitos(json.dumps(payload)))
