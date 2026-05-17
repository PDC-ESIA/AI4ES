Implemente o fluxo de autenticação de usuário em FastAPI.

Requisitos funcionais:
- POST /auth/register: recebe email e senha, valida formato do email, persiste usuário com senha hasheada (bcrypt), retorna 201 com user_id
- POST /auth/login: recebe email e senha, valida, retorna JWT com expiração de 8 horas
- GET /auth/me: requer Authorization Bearer JWT, retorna dados do usuário autenticado
- Bloquear usuário após 5 tentativas de login falhas em sequência (reset em 30 min)

Requisitos não-funcionais:
- Stack: Python 3.12, FastAPI, SQLite, PyJWT, bcrypt
- Testes pytest para cada endpoint (happy path + 1 edge case por endpoint)
- Estrutura: src/auth/{routes.py, models.py, schemas.py, service.py} + tests/test_auth.py

Objetivo: exercitar o pipeline SDLC completo com requisitos não-triviais.
