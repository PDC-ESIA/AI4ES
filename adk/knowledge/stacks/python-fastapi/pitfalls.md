# Pitfalls — stack `python-fastapi`

## SQLAlchemy — relationship() exige ForeignKey

Toda `relationship("ModelFilho", ...)` no model PAI exige que o model FILHO tenha uma
coluna com `ForeignKey("tabela_pai.id")`. Sem ForeignKey → `NoForeignKeysError` → crash na
primeira query. Use `back_populates` (não `backref`) para clareza bidirecional.

Exemplo correto:

```python
class Ensaio(Base):
    __tablename__ = "ensaios"
    id = Column(Integer, primary_key=True)
    fotos = relationship("Foto", back_populates="ensaio")

class Foto(Base):  # FILHO — ForeignKey obrigatória
    __tablename__ = "fotos"
    id = Column(Integer, primary_key=True)
    ensaio_id = Column(Integer, ForeignKey("ensaios.id"), nullable=False)
    ensaio = relationship("Ensaio", back_populates="fotos")
```

## Jinja2Templates.TemplateResponse — use a API nova

Use a API NOVA (Starlette >= 1.0): `request` é o PRIMEIRO argumento posicional, nunca
dentro do dict de contexto. A assinatura antiga quebra com
`TypeError: unhashable type: 'dict'` → HTTP 500 em toda rota que renderiza template.

Correto: `templates.TemplateResponse(request, "login.html", {"titulo": "Login"})`
Errado (assinatura antiga, nunca use): `templates.TemplateResponse("login.html", {"request": request, "titulo": "Login"})`

## Arquivos que o pytest exige para coletar testes

Sem estes 3 arquivos, `tests/test_*.py` que fazem `from app.main import app` falha com
`ModuleNotFoundError: No module named 'app'`:

- `app/__init__.py` (vazio basta) — torna `app` pacote importável
- `tests/__init__.py` (vazio basta) — torna `tests` pacote
- `conftest.py` na raiz (vazio basta) — pytest usa para detectar rootdir

Crie os 3 SEMPRE que entregar um projeto Python testável.

## requirements.txt precisa refletir os imports reais

Todo `import X` / `from X import ...` no código DEVE ter o pacote correspondente no
`requirements.txt`. Atenção a nome de import != nome de pacote — ver `deps.md` neste
diretório para a tabela de alias conhecida (ex.: `from PIL import Image` exige o pacote
`Pillow`, não `PIL`).

## Dockerfile — COPY só o que existe

Verifique a estrutura de diretórios criada antes de escrever `COPY` — não copie nada que
você não criou via tool de escrita. Se o código está em `app/`, use `COPY app/ /app/app/`.
O `CMD` deve referenciar o módulo EXATO onde está `app = FastAPI()` (ex.: se está em
`app/main.py`, use `uvicorn app.main:app`).

## SQLite com path relativo em container

A porta mapeada no `docker-compose.yml` deve corresponder à porta no `CMD`/`EXPOSE` do
Dockerfile. Se o app usa SQLite com path relativo, o container precisa ter o diretório —
adicione `RUN mkdir -p /app/data` no Dockerfile se necessário.

## Sinais de erro conhecidos (mapa rápido)

| Sinal (erro observado) | Correção |
|---|---|
| `No matching distribution found for X` | Remova o pacote inválido do `requirements.txt` |
| `NoForeignKeysError` | Adicione a ForeignKey faltante no model filho |
| `ModuleNotFoundError: No module named 'X'` | Adicione o pacote ao `requirements.txt` |
| `ImportError: X is not installed` | Adicione a dependência ao `requirements.txt` |
| `Could not import module 'app.main'` | Corrija o `CMD` do Dockerfile ou os imports |
| `COPY failed: file not found` | Ajuste o `COPY` no Dockerfile para paths existentes |
| `NameError: name 'X' is not defined` | Adicione o import faltante no arquivo indicado |
