# Fluxo de Recepção de Requisitos e Geração Paralela de Testes

---

## 1. Contexto

| Campo | Valor |
|---|---|
| Origem dos artefatos | `[ PREENCHER: ex: caminho dos artefatos da etapa de codificação` |
| Formato inicial adotado | `[ PREENCHER: RF / HU / UC / RNF / RN ]` |
| Número típico de artefatos por ciclo | `[ PREENCHER: ex: 5 a 20 ]` |
| Limite máximo de tarefas paralelas | `[ PREENCHER: ex: 5 ]` |
| Pasta de destino dos testes gerados | `[ PREENCHER: ex: adk/src/agents/tests/artefactsTests/ ]` |

---

## 2. Por que Paralelismo?

```
Sem paralelismo — sequencial:
Artefato-1 → gera teste (Xs) → Artefato-2 → gera teste (Xs) → Artefato-3 → gera teste (Xs)
Tempo total: 3× o tempo de um artefato

Com paralelismo — asyncio.gather:
Artefato-1 ─┐
Artefato-2 ─┼─ geram testes ao mesmo tempo (~Xs)
Artefato-3 ─┘
Tempo total: ~igual ao tempo de um único artefato
```

Quando o volume de artefatos for grande, o paralelismo é essencial para manter o agente responsivo.

---

## 3. Fluxo Completo

```
  [ PREENCHER: origem dos artefatos do código]
         │
         │  artefatos extraídos/recebidos
         ▼
  [ lista de artefatos: Artefato-1, Artefato-2, ... ]
         │
         │  via Supervisor Agent (ou diretamente no MVP)
         ▼
┌─────────────────────────────┐
│         QA Agent            │
│   receber_requisitos()      │
│   recebe lista de artefatos │
└──────────────┬──────────────┘
               │
               │  asyncio.gather() — dispara tudo em paralelo
               │
   ┌───────────┼───────────┐
   ▼           ▼           ▼
[Artefato-1] [Artefato-2] [Artefato-3]
   │             │             │
   │  cada um executa independentemente:
   │  1. analisa artefato
   │  2. gera código pytest
   │  3. salva arquivo .py em [ PREENCHER: tests/ ]
   │
   └─────────────┼─────────────┘
                 │
                 ▼
┌─────────────────────────────┐
│  asyncio.gather() coleta    │
│  todos os resultados        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Consolida relatório e      │
│  retorna ao chamador        │
└─────────────────────────────┘
```

---

## 4. Implementação

### 4.1 Função principal — processa lista de artefatos em paralelo

```python
# arquivo: [ PREENCHER: ex: adk/src/agents/qa_agent/qa_agent.py ]

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger("qa_agent")

# [ PREENCHER: ajuste o caminho de destino dos testes gerados ]
TESTS_DIR = Path("[ PREENCHER: ex: adk/src/agents/tests/artefactsTests/ ]")


def receber_requisitos(artefatos_json: str) -> dict:
    """
    Ponto de entrada do QA Agent para processar múltiplos artefatos.

    Aceita uma lista de artefatos em JSON e os processa em paralelo.

    Args:
        artefatos_json: String JSON com lista de artefatos.
          Formato:
          '[
            {"id_artefato": "RF-001", "tipo": "RF", "conteudo": "...", "modulo": "..."},
            {"id_artefato": "RF-002", "tipo": "RF", "conteudo": "...", "modulo": "..."}
          ]'

    Returns:
        Relatório consolidado com status de cada artefato.
    """
    try:
        lista = json.loads(artefatos_json)
        if isinstance(lista, dict):
            lista = [lista]  # aceita também um único artefato
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido: {e}")
            arquivo_duvida = asyncio.run(_gerar_doubt_artifact(
                "ERR_ENTRADA_JSON",
                f"Erro ao fazer parse do JSON de entrada: {e}"
            ))
            return {
                "status": "erro",
                "mensagem": f"JSON inválido: {e}",
                "arquivo_duvida": arquivo_duvida,
            }

    resultados = asyncio.run(_processar_todos_em_paralelo(lista))

    total = len(resultados)
    sucessos = sum(1 for r in resultados if r["status"] == "sucesso")

    return {
        "status": "concluido",
        "resumo": {
            "total": total,
            "sucessos": sucessos,
            "falhas": total - sucessos,
        },
        "detalhes": resultados,
    }


async def _processar_todos_em_paralelo(
    lista_artefatos: list,
    max_paralelos: int = 5,  # [ PREENCHER: ajuste conforme o ambiente ]
) -> list:
    """
    Dispara o processamento de todos os artefatos ao mesmo tempo.
    O Semaphore garante que no máximo `max_paralelos` rodem simultaneamente.
    """
    semaforo = asyncio.Semaphore(max_paralelos)

    async def processar_com_limite(artefato):
        async with semaforo:
            return await _processar_artefato(artefato)

    tarefas = [processar_com_limite(a) for a in lista_artefatos]
    return await asyncio.gather(*tarefas)


async def _processar_artefato(artefato: dict) -> dict:
    """
    Processa um único artefato:
    1. Valida o artefato — gera Doubt_Artifact.md se houver inconsistência
    2. Gera o código pytest correspondente
    3. Salva o arquivo .py na pasta de testes
    4. Retorna o resultado
    """
    id_artefato = artefato.get("id_artefato", "SEM_ID")
    tipo        = artefato.get("tipo", "RF")
    conteudo    = artefato.get("conteudo", "")
    modulo      = artefato.get("modulo", "geral")

    logger.info(f"[QA] Iniciando: {id_artefato} ({tipo})")

    # ── Regra obrigatória: Doubt Artifact ─────────────────────────────────────
    # Se o artefato estiver incompleto ou inconsistente, pausar e gerar dúvida.
    # [ PREENCHER: adicione outras validações específicas do seu projeto ]
    bloqueio = _validar_artefato(artefato)
    if bloqueio:
        arquivo_duvida = await _gerar_doubt_artifact(id_artefato, bloqueio)
        logger.warning(f"[QA] Bloqueado: {id_artefato} → {arquivo_duvida}")
        return {
            "id_artefato": id_artefato,
            "status": "bloqueado",
            "motivo": "doubt_artifact_gerado",
            "arquivo_duvida": arquivo_duvida,
            "mensagem": f"Inconsistência encontrada: {bloqueio}. Aguardando intervenção humana.",
        }
    # ──────────────────────────────────────────────────────────────────────────

    try:
        codigo_teste = await _gerar_codigo_pytest(id_artefato, tipo, conteudo, modulo)

        TESTS_DIR.mkdir(parents=True, exist_ok=True)

        # [ PREENCHER: ajuste o padrão de nomenclatura se necessário ]
        nome_arquivo = f"test_{tipo.lower()}_{id_artefato.lower().replace('-', '_')}.py"
        caminho = TESTS_DIR / nome_arquivo
        caminho.write_text(codigo_teste, encoding="utf-8")

        logger.info(f"[QA] Concluído: {id_artefato} → {caminho}")

        return {
            "id_artefato": id_artefato,
            "status": "sucesso",
            "arquivo_gerado": str(caminho),
            "erro": None,
        }

    except Exception as e:
        logger.error(f"[QA] Erro em {id_artefato}: {e}")
        return {
            "id_artefato": id_artefato,
            "status": "falha",
            "arquivo_gerado": None,
            "erro": str(e),
        }


def _validar_artefato(artefato: dict) -> str | None:
    """
    Valida se o artefato tem informações suficientes para gerar testes.
    Retorna uma string descrevendo o bloqueio, ou None se estiver ok.

    [ PREENCHER: adicione validações específicas do seu projeto ]
    """
    if not artefato.get("conteudo", "").strip():
        return "Campo 'conteudo' está vazio — não é possível gerar testes sem descrição do requisito."

    if not artefato.get("modulo", "").strip():
        return "Campo 'modulo' está vazio — não é possível identificar o código a ser testado."

    if artefato.get("tipo") not in ("RF", "HU", "UC", "RNF", "RN"):
        return f"Tipo de artefato desconhecido: '{artefato.get('tipo')}'. Esperado: RF, HU, UC, RNF ou RN."

    # [ PREENCHER: adicione outras validações ]
    return None


async def _gerar_doubt_artifact(id_artefato: str, motivo: str) -> str:
    """
    Gera o arquivo Doubt_Artifact.md e retorna o caminho do arquivo criado.
    O nó é pausado — a execução só retoma após intervenção humana.
    """
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    doubt_dir = TESTS_DIR.parent / "doubt_artifacts"
    doubt_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
    caminho = doubt_dir / nome_arquivo

    conteudo = f"""# Doubt Artifact — QA Agent

**ID do Artefato:** {id_artefato}
**Data/Hora:** {timestamp}
**Agente:** qa_agent
**Status:** BLOQUEADO — aguardando intervenção humana

---

## Descrição do Bloqueio

{motivo}

## O que é necessário para continuar

[ PREENCHER após intervenção: descreva o que foi fornecido ou decidido para desbloquear ]

## Resolução

- **Resolvido por:** [ PREENCHER ]
- **Data:** [ PREENCHER ]
- **Ação tomada:** [ PREENCHER ]
"""

    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)


async def _gerar_codigo_pytest(
    id_artefato: str, tipo: str, conteudo: str, modulo: str
) -> str:
    """
    [ PREENCHER: implemente a geração do código pytest aqui ]

    Sugestões de implementação:
    - Chamar o modelo via ADK para interpretar o artefato e escrever os testes
    - Usar templates por tipo de artefato (RF, HU, UC...)
    - Combinar templates + LLM para personalização
    """
    # Placeholder — substitua pela sua lógica:
    classe = f"Test{tipo}{id_artefato.replace('-', '')}"
    return f'''
    Testes gerados automaticamente pelo QA Agent
    Artefato: {id_artefato} ({tipo}) | Módulo: {modulo}
    Requisito: {conteudo}
    """

    import pytest
    # [ PREENCHER: importar módulos da aplicação sendo testada ]


    class {classe}:
        """Suite de testes para {id_artefato}"""

        def test_caminho_feliz(self):
            # [ PREENCHER ]
            pass

        def test_entrada_invalida(self):
            with pytest.raises(Exception):
                pass  # [ PREENCHER ]

        def test_caso_de_borda(self):
            pass  # [ PREENCHER ]
    '''
```

---

## 5. Priorização por Criticidade

Antes de disparar o paralelismo, ordene os artefatos para que os mais críticos sejam processados primeiro:

```python
def ordenar_por_criticidade(lista_artefatos: list) -> list:
    """Garante que artefatos críticos apareçam no topo do relatório."""
    prioridade = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(
        lista_artefatos,
        key=lambda a: prioridade.get(a.get("criticidade", "media"), 1)
    )

# Uso antes de _processar_todos_em_paralelo:
lista_ordenada = ordenar_por_criticidade(lista_artefatos)
resultados = await _processar_todos_em_paralelo(lista_ordenada)
```

---

## 6. Controle de Lotes (para volumes grandes)

Se o ciclo tiver muitos artefatos, processe em lotes para não sobrecarregar o ambiente:

```python
def dividir_em_lotes(lista: list, tamanho: int) -> list:
    return [lista[i:i + tamanho] for i in range(0, len(lista), tamanho)]


async def processar_em_lotes(lista_artefatos: list) -> list:
    TAMANHO_LOTE = [ ]  # [ PREENCHER: ex: 5 ]
    lotes = dividir_em_lotes(lista_artefatos, TAMANHO_LOTE)

    todos = []
    for i, lote in enumerate(lotes, 1):
        logger.info(f"Processando lote {i}/{len(lotes)}...")
        resultados = await _processar_todos_em_paralelo(lote)
        todos.extend(resultados)
    return todos
```

---

## 7. Doubt Artifacts no Fluxo Paralelo

> **Regra de arquitetura do projeto:** Obrigatoriamente, todos os agentes devem gerar `Doubt_Artifact.md` ao encontrar inconsistências ou bloqueios, pausando a execução do nó.

### Comportamento no contexto paralelo

Como múltiplos artefatos são processados ao mesmo tempo, o Doubt Artifact **não interrompe toda a fila** — apenas o artefato problemático é pausado. Os demais continuam normalmente.

```
asyncio.gather() disparou 3 artefatos em paralelo:

  RF-001 ──→ validação ok ──→ gera teste ──→ sucesso ✅
  RF-002 ──→ inconsistência ──→ Doubt_Artifact.md ──→ status: bloqueado ⏸
  RF-003 ──→ validação ok ──→ gera teste ──→ sucesso ✅

Relatório final:
  { total: 3, sucessos: 2, bloqueados: 1, falhas: 0 }
```

### Estrutura de pastas

```
[ PREENCHER: pasta do agente ]/
├── tests/               ← testes gerados com sucesso
│   ├── test_rf_001.py
│   └── test_rf_003.py
└── doubt_artifacts/     ← artefatos com bloqueio aguardando humano
    └── Doubt_Artifact_RF-002_20260317T140000.md
```

### O que o relatório final deve indicar

```python
# O campo "bloqueados" deve ser adicionado ao resumo consolidado
return {
    "status": "concluido",
    "resumo": {
        "total": total,
        "sucessos": sucessos,
        "bloqueados": bloqueados,   # ← artefatos com Doubt Artifact pendente
        "falhas": falhas,
    },
    "detalhes": resultados,         # inclui os de status "bloqueado"
}
```

---
