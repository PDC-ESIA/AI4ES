Construa um endpoint /healthcheck simples em FastAPI que retorne {"status": "ok"}.

Requisitos:
- Stack: Python 3.12, FastAPI 0.115+
- Sem banco de dados
- Incluir teste pytest que verifique GET /healthcheck → 200 com body {"status": "ok"}
- Estrutura mínima: um arquivo main.py + um test_main.py

Objetivo do teste: validar o ciclo SDLC end-to-end do orchestrator (requirements → design → coding → review → qa).
