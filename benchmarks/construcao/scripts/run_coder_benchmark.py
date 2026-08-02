"""Runner/Orquestrador do Benchmark para o Agente de Construção (Coder Agent).

Este script realiza a leitura das tarefas do subconjunto (HumanEval/MBPP),
configura e invoca o coder_agent programaticamente sob o modelo selecionado,
e direciona a execução das tarefas para a sandbox de testes, gravando os
resultados estruturados (JSON) na pasta resultados/exec_logs/.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configura logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.run_coder")


def load_dataset(dataset_name: str) -> list:
    """Lê o arquivo .jsonl correspondente ao dataset selecionado e retorna as tarefas."""
    # TODO: Implementar leitura do dataset_name_subset.jsonl na pasta tarefas/
    logger.info(f"Carregando dataset: {dataset_name}")
    return []


def run_benchmark(model_name: str, dataset_name: str, num_runs: int, use_docker: bool):
    """Executa o loop de benchmark para o dataset e modelo indicados."""
    logger.info(
        f"Iniciando benchmark: Modelo={model_name} | Dataset={dataset_name} | Runs={num_runs} | Docker={use_docker}"
    )
    
    # 1. Carrega tarefas
    tasks = load_dataset(dataset_name)
    if not tasks:
        logger.warning("Nenhuma tarefa carregada. Finalizando.")
        return
        
    # 2. Executa loop de tarefas e rodadas
    # TODO: Integrar com a inicialização do coder_agent desabilitando trava HITL.
    # TODO: Para cada tarefa e rodada, coletar tempo, tokens, gerar arquivo no workspace temporário,
    #       executar evaluate_sandbox.py, e gravar o log JSON final em resultados/exec_logs/.
    logger.info("Benchmark concluído com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquestrador de Benchmark do Coder Agent")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Nome do modelo de LLM")
    parser.add_argument("--dataset", type=str, choices=["humaneval", "mbpp"], default="humaneval", help="Dataset alvo")
    parser.add_argument("--runs", type=int, default=10, help="Quantidade de repetições por problema")
    parser.add_argument("--docker", action="store_true", help="Executar testes unitários dentro de container Docker")
    
    args = parser.parse_args()
    run_benchmark(args.model, args.dataset, args.runs, args.docker)
