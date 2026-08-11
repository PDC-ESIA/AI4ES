"""Orquestração do subagente receive_requirements: entrypoint da tool, paralelismo e priorização."""

import asyncio
import json
import logging
import os

from .io import _gerar_doubt_artifact, _salvar_arquivos_apoio, _slugify, _tests_dir
from .llm_generation import _gerar_pytest_via_llm, _parse_fragmented_requirements
from .normalizer import _normalizar_anexos_inline
from .sanitizer import _validar_e_sanitizar_codigo

logger = logging.getLogger("qa_agent")


def _run_async(coro):
    """Executa coroutine de forma segura com ou sem event loop ativo.

    Args:
        coro: Coroutine a ser executada.

    Returns:
        Resultado da coroutine.

    Note:
        Compatível com FastAPI + ADK - usa ThreadPoolExecutor se houver loop ativo.
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
        logger.warning(f"[QA] Falha ao ler JSON estrito. Tentando extrair de fragmentos de texto...")
        try:
            lista = _parse_fragmented_requirements(artefatos_json)
        except Exception as fallback_e:
            caminho = _run_async(
                _gerar_doubt_artifact("ERR_ENTRADA_JSON", f"Erro ao parsear JSON de entrada: {e}")
            )
            return {
                "status": "erro",
                "mensagem": f"JSON inválido: {e}",
                "arquivo_duvida": caminho,
            }

    lista = _normalizar_anexos_inline(lista)
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


async def _processar_todos_em_paralelo(
    lista_artefatos: list,
    max_paralelos: int | None = None,
) -> list:
    """Processa múltiplos artefatos em paralelo com limite de concorrência.

    Args:
        lista_artefatos: Lista de artefatos de requisito.
        max_paralelos: Máximo de processamentos (chamadas ao LLM) simultâneos.
            Se None, lê da env var QA_AGENT_MAX_PARALELOS (padrão: 5).

    Returns:
        list: Lista de resultados de cada artefato processado.
    """
    if max_paralelos is None:
        max_paralelos = int(os.environ.get("QA_AGENT_MAX_PARALELOS", "5"))
    semaforo = asyncio.Semaphore(max_paralelos)

    async def processar_com_limite(artefato):
        async with semaforo:
            return await _processar_artefato(artefato)

    return await asyncio.gather(*[processar_com_limite(a) for a in lista_artefatos])


async def _processar_artefato(artefato: dict) -> dict:
    """Processa um único artefato de requisito gerando teste pytest.

    Args:
        artefato: Dicionário com id_artefato, tipo, conteudo, modulo, criticidade.

    Returns:
        dict: Resultado com status (sucesso/bloqueado/falha) e caminhos gerados.
    """
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
        slug = _slugify(id_artefato)
        artefato_dir = _tests_dir() / slug
        artefato_dir.mkdir(parents=True, exist_ok=True)
        (artefato_dir / "__init__.py").touch(exist_ok=True)

        anexos_salvos = _salvar_arquivos_apoio(artefato, artefato_dir)
        tem_codigo = any(p.suffix in ['.py', '.java', '.js', '.c'] for p in anexos_salvos)

        nomes_anexos = [p.name for p in anexos_salvos]
        if nomes_anexos:
            logger.info(f"[QA] Arquivos anexados detectados para {id_artefato}: {nomes_anexos}")
        else:
            logger.info(f"[QA] Nenhum arquivo anexado detectado para {id_artefato}.")

        nome_teste = f"test_{slug}.py"
        caminho = artefato_dir / nome_teste

        codigo = _gerar_pytest_via_llm(
            id_artefato=id_artefato,
            tipo=tipo,
            conteudo=conteudo,
            modulo=modulo,
            arquivos_apoio=anexos_salvos,
            nome_teste=nome_teste,
        )
        codigo_valido = _validar_e_sanitizar_codigo(codigo, id_artefato)
        caminho.write_text(codigo_valido, encoding="utf-8")

        logger.info(f"[QA] Concluído (Fluxo {'A' if tem_codigo else 'B'}): {id_artefato} → {caminho}")
        return {
            "id_artefato": id_artefato,
            "status": "sucesso",
            "fluxo": "A" if tem_codigo else "B",
            "pasta_gerada": str(artefato_dir),
            "arquivo_gerado": str(caminho),
            "arquivos_apoio": [str(p) for p in anexos_salvos],
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
    """Valida artefato de requisito verificando campos obrigatórios.

    Args:
        artefato: Dicionário com campos do artefato.

    Returns:
        str | None: Descrição do bloqueio ou None se válido.
    """
    if not artefato.get("conteudo", "").strip():
        return "Campo 'conteudo' vazio — impossível gerar testes sem descrição do requisito."
    if not artefato.get("modulo", "").strip():
        artefato["modulo"] = "geral"
    if artefato.get("tipo") not in ("RF", "HU", "UC", "RNF", "RN"):
        return (
            f"Tipo desconhecido: '{artefato.get('tipo')}'. "
            "Esperado: RF, HU, UC, RNF ou RN."
        )
    return None


def _ordenar_por_criticidade(lista: list) -> list:
    """Ordena lista de artefatos por criticidade (alta > media > baixa).

    Args:
        lista: Lista de artefatos com campo criticidade.

    Returns:
        list: Lista ordenada por prioridade.
    """
    prioridade = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(lista, key=lambda a: prioridade.get(a.get("criticidade", "media"), 1))
