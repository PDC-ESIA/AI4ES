import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("qa_agent")

# Caminhos base — relativos à raiz do agente
_BASE_DIR = Path(__file__).parent.parent
TESTS_DIR = _BASE_DIR / "artefactsTests"
DOUBT_DIR = _BASE_DIR / "doubt_artifacts"

# ──────────────────────────────────────────────────────────────────────────────
# Ponto de entrada público (registrado como FunctionTool no agent.py)
# ──────────────────────────────────────────────────────────────────────────────

def _run_async(coro):
    """
    Executa uma coroutine de forma segura independente de haver
    um event loop rodando ou não (compatível com FastAPI + ADK).
    """
    try:
        asyncio.get_running_loop()
        # Há um loop rodando (FastAPI/ADK) — executa em thread separada
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # Sem loop rodando — pode usar asyncio.run normalmente
        return asyncio.run(coro)


def receber_requisitos(artefatos_json: str) -> dict:
    """
    Recebe uma lista de artefatos de requisito em JSON e gera testes pytest
    em paralelo para cada um.

    Args:
        artefatos_json: String JSON com um ou mais artefatos.
            Formato de um artefato:
            {
                "id_artefato": "RF-001",
                "tipo": "RF",
                "conteudo": "O sistema deve...",
                "modulo": "nome_do_modulo",
                "criticidade": "alta"
            }

    Returns:
        Relatório consolidado:
        {
            "status": "concluido",
            "resumo": { "total": N, "sucessos": N, "bloqueados": N, "falhas": N },
            "detalhes": [ ... ]
        }
    """
    try:
        lista = json.loads(artefatos_json)
        if isinstance(lista, dict):
            lista = [lista]
    except json.JSONDecodeError as e:
        logger.error(f"[QA] JSON inválido: {e}")
        caminho = _run_async(
            _gerar_doubt_artifact("ERR_ENTRADA_JSON", f"Erro ao parsear JSON de entrada: {e}")
        )
        return {
            "status": "erro",
            "mensagem": f"JSON inválido: {e}",
            "arquivo_duvida": caminho,
        }

    lista = _ordenar_por_criticidade(lista)
    resultados = _run_async(_processar_todos_em_paralelo(lista))

    total     = len(resultados)
    sucessos  = sum(1 for r in resultados if r["status"] == "sucesso")
    bloqueados = sum(1 for r in resultados if r["status"] == "bloqueado")
    falhas    = total - sucessos - bloqueados

    return {
        "status": "concluido",
        "resumo": {
            "total": total,
            "sucessos": sucessos,
            "bloqueados": bloqueados,
            "falhas": falhas,
        },
        "detalhes": resultados,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Processamento paralelo
# ──────────────────────────────────────────────────────────────────────────────

async def _processar_todos_em_paralelo(
    lista_artefatos: list,
    max_paralelos: int = 5,
) -> list:
    semaforo = asyncio.Semaphore(max_paralelos)

    async def processar_com_limite(artefato):
        async with semaforo:
            return await _processar_artefato(artefato)

    return await asyncio.gather(*[processar_com_limite(a) for a in lista_artefatos])


async def _processar_artefato(artefato: dict) -> dict:
    id_artefato = artefato.get("id_artefato", "SEM_ID")
    tipo        = artefato.get("tipo", "RF")
    conteudo    = artefato.get("conteudo", "")
    modulo      = artefato.get("modulo", "geral")

    logger.info(f"[QA] Iniciando: {id_artefato} ({tipo})")

    # Valida antes de gerar
    bloqueio = _validar_artefato(artefato)
    if bloqueio:
        caminho = await _gerar_doubt_artifact(id_artefato, bloqueio)
        logger.warning(f"[QA] Bloqueado: {id_artefato} → {caminho}")
        return {
            "id_artefato": id_artefato,
            "status": "bloqueado",
            "motivo": "doubt_artifact_gerado",
            "arquivo_duvida": str(caminho),
            "mensagem": f"Inconsistência: {bloqueio}. Aguardando intervenção humana.",
        }

    try:
        codigo = _gerar_template_pytest(id_artefato, tipo, conteudo, modulo)

        TESTS_DIR.mkdir(parents=True, exist_ok=True)
        nome = f"test_{id_artefato.lower().replace('-', '_')}.py"
        caminho = TESTS_DIR / nome
        caminho.write_text(codigo, encoding="utf-8")

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


# ──────────────────────────────────────────────────────────────────────────────
# Validação
# ──────────────────────────────────────────────────────────────────────────────

def _validar_artefato(artefato: dict) -> str | None:
    """Retorna descrição do bloqueio ou None se o artefato estiver ok."""
    if not artefato.get("conteudo", "").strip():
        return "Campo 'conteudo' vazio — impossível gerar testes sem descrição do requisito."
    if not artefato.get("modulo", "").strip():
        return "Campo 'modulo' vazio — impossível identificar o código a ser testado."
    if artefato.get("tipo") not in ("RF", "HU", "UC", "RNF", "RN"):
        return (
            f"Tipo desconhecido: '{artefato.get('tipo')}'. "
            "Esperado: RF, HU, UC, RNF ou RN."
        )
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Doubt Artifact
# ──────────────────────────────────────────────────────────────────────────────

async def _gerar_doubt_artifact(id_artefato: str, motivo: str) -> str:
    """Gera Doubt_Artifact.md e retorna o caminho do arquivo criado."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    DOUBT_DIR.mkdir(parents=True, exist_ok=True)

    nome = f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
    caminho = DOUBT_DIR / nome

    conteudo = f"""# Doubt Artifact — QA Agent

**ID do Artefato:** {id_artefato}
**Data/Hora:** {timestamp}
**Agente:** qa_agent
**Status:** BLOQUEADO — aguardando intervenção humana

---

## Descrição do Bloqueio

{motivo}

## O que é necessário para continuar

[ Preencher após intervenção ]

## Resolução

- **Resolvido por:** [ Preencher ]
- **Data:** [ Preencher ]
- **Ação tomada:** [ Preencher ]
"""
    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)


# ──────────────────────────────────────────────────────────────────────────────
# Geração do template pytest
# ──────────────────────────────────────────────────────────────────────────────

def _gerar_template_pytest(
    id_artefato: str, tipo: str, conteudo: str, modulo: str
) -> str:
    """
    Gera o esqueleto pytest para o artefato.
    TODO: substituir por chamada ao modelo Gemini para geração inteligente.
    """
    classe = f"Test{tipo}{id_artefato.replace('-', '')}"
    return f'''"""
Testes gerados automaticamente pelo QA Agent — PDC-AI4SE
Artefato : {id_artefato} ({tipo})
Módulo   : {modulo}
Requisito: {conteudo}
"""

import pytest
# TODO: from src.<modulo> import <funcao>


class {classe}:
    """Suite de testes para {id_artefato}."""

    def test_caminho_feliz(self):
        """Comportamento correto com entradas válidas."""
        # Arrange
        # Act
        # Assert
        pass  # TODO: implementar

    def test_entrada_invalida(self):
        """Comportamento com entradas incorretas."""
        with pytest.raises(Exception):
            pass  # TODO: implementar

    def test_caso_de_borda(self):
        """Comportamento em casos extremos (vazio, zero, máximo, etc.)."""
        pass  # TODO: implementar
'''


# ──────────────────────────────────────────────────────────────────────────────
# Priorização
# ──────────────────────────────────────────────────────────────────────────────

def _ordenar_por_criticidade(lista: list) -> list:
    prioridade = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(lista, key=lambda a: prioridade.get(a.get("criticidade", "media"), 1))