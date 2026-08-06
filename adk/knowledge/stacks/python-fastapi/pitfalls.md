# Pitfalls — stack `python-fastapi`

> Escopo: `stack:python-fastapi`. Semente manual, curada à mão, estável — não sofre
> `grow-and-refine` automático (isso é papel de `lessons.md` neste mesmo diretório; os dois
> convivem porque têm política de escrita diferente — relatório §12.4). Migrado do bloco
> `# ERROS COMUNS — EVITE A TODO CUSTO`, hardcoded em
> `src/agents/workflow_coding_review/cr_coder.py` até a issue #303. `proveniencia` de cada
> item aponta pro commit/arquivo de origem real, verificado no histórico do repositório —
> não inferido.

---

```yaml
trigger:       relationship() do SQLAlchemy sem ForeignKey correspondente no model filho
granularidade: evento
corpo: >
  Toda `relationship("ModelFilho", ...)` no model PAI exige que o model FILHO tenha uma
  coluna com `ForeignKey("tabela_pai.id")`. Sem ForeignKey → `NoForeignKeysError` → crash
  na primeira query. Use `back_populates` (não `backref`) para clareza bidirecional.
  Exemplo correto:
    class Ensaio(Base):
        __tablename__ = "ensaios"
        id = Column(Integer, primary_key=True)
        fotos = relationship("Foto", back_populates="ensaio")

    class Foto(Base):  # FILHO — ForeignKey obrigatória
        __tablename__ = "fotos"
        id = Column(Integer, primary_key=True)
        ensaio_id = Column(Integer, ForeignKey("ensaios.id"), nullable=False)
        ensaio = relationship("Ensaio", back_populates="fotos")
evidencia:     null
escopo:        stack:python-fastapi
status:        ativo
proveniencia:  semente manual (cr_coder.py, pré-#303)
```

---

```yaml
trigger:       Jinja2Templates.TemplateResponse em rota FastAPI
granularidade: evento
corpo: >
  Use a API NOVA (Starlette >= 1.0): `request` é o PRIMEIRO argumento posicional, nunca
  dentro do dict de contexto. A assinatura antiga quebra com
  `TypeError: unhashable type: 'dict'` → HTTP 500 em toda rota que renderiza template.
  Correto:
    return templates.TemplateResponse(request, "login.html", {"titulo": "Login"})
  Errado (assinatura antiga, nunca use):
    return templates.TemplateResponse("login.html", {"request": request, "titulo": "Login"})
evidencia:     commit 6a35751 ("fix(coder): #303 corrige API do Jinja2Templates.TemplateResponse no prompt do cr_coder")
escopo:        stack:python-fastapi
status:        ativo
proveniencia:  cr_coder.py, commit 6a35751
```

---

```yaml
trigger:       criação de projeto Python testável com pytest
granularidade: evento
corpo: >
  pytest exige estes 3 arquivos para coletar `tests/test_*.py` que fazem
  `from app.main import app` — sem eles, falha com
  `ModuleNotFoundError: No module named 'app'`:
    - app/__init__.py     (vazio basta) — torna `app` pacote importável
    - tests/__init__.py   (vazio basta) — torna `tests` pacote
    - conftest.py na raiz (vazio basta) — pytest usa para detectar rootdir
  Crie os 3 SEMPRE que entregar um projeto Python testável.
evidencia:     null
escopo:        stack:python-fastapi
status:        ativo
proveniencia:  semente manual (coder/prompt.py, "DIRETRIZES DE CODIFICAÇÃO", item 4)
```

---

```yaml
trigger:       requirements.txt divergente do que o código de fato importa
granularidade: evento
corpo: >
  Todo `import X` / `from X import ...` no código DEVE ter o pacote correspondente no
  requirements.txt. Atenção a nome de import != nome de pacote (ver deps.md deste
  diretório para a tabela de alias conhecida — ex.: `from PIL import Image` exige o
  pacote `Pillow`, não `PIL`).
evidencia:     shared/tools/coding_tools/verificacao_dependencias.py
escopo:        stack:python-fastapi
status:        ativo
proveniencia:  semente manual (cr_coder.py, pré-#303); reforçado pelo gate da #303
```

---

```yaml
trigger:       instrução COPY no Dockerfile para app Python
granularidade: evento
corpo: >
  Verifique a estrutura de diretórios criada antes de escrever COPY — não copie nada que
  você não criou via tool de escrita. Se o código está em `app/`, use
  `COPY app/ /app/app/`. O CMD deve referenciar o módulo EXATO onde está `app = FastAPI()`
  (ex.: se está em `app/main.py`, use `uvicorn app.main:app`).
evidencia:     null
escopo:        stack:python-fastapi
status:        ativo
proveniencia:  semente manual (cr_coder.py, pré-#303)
```

---

```yaml
trigger:       app usa SQLite com path relativo em container Docker
granularidade: evento
corpo: >
  A porta mapeada no docker-compose.yml deve corresponder à porta no CMD/EXPOSE do
  Dockerfile (ver core/consistency-rules.md). Se o app usa SQLite com path relativo, o
  container precisa ter o diretório — adicione `RUN mkdir -p /app/data` no Dockerfile se
  necessário.
evidencia:     null
escopo:        stack:python-fastapi
status:        ativo
proveniencia:  semente manual (cr_coder.py, pré-#303)
```
