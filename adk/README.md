## Execução Local

```bash
uv sync
```

Linux:
```bash
source .venv/bin/activate
uvicorn main:app --reload --port 8081
```

Windows:
```bash
.venv\Scripts\activate
uvicorn main:app --reload --port 8081
```

## Teste


```
http://127.0.0.1:8000/dev-ui/?app=teste_timeo
```
