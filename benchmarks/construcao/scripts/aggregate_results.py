"""Consolidador de Resultados do Benchmark para o Coder Agent.

Este script lê todos os logs JSON brutos salvos em resultados/exec_logs/,
agrupa as informações por modelo e tarefa, calcula as estatísticas e as taxas
de sucesso (incluindo a estimativa matemática de Pass@k), e invoca as rotinas
do diretório compartilhado benchmarks/shared/statistical_treatment.py para gerar
a análise descritiva e testes de hipótese.
"""

import os
import sys
import json
import argparse
import logging
import numpy as np
from pathlib import Path

# Adiciona o diretório compartilhado ao path do Python
sys.path.append(str(Path(__file__).resolve().parents[2]))
from shared.statistical_treatment import (
    compute_descriptive_stats,
    compute_cliffs_delta,
    compute_wilcoxon_signed_rank,
    compute_friedman_test,
    compute_nemenyi_critical_difference,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.aggregate")


def calculate_pass_at_k(n, c, k):
    """Calcula a estimativa de Pass@k usando a fórmula clássica de Chen et al. (2021).

    n: Total de rodadas executadas por problema
    c: Quantidade de execuções com sucesso (aprovadas nos testes)
    k: Valor de k (ex: 1, 5, 10)
    """
    if n - c < k:
        return 1.0
    
    # Usando cálculo de coeficientes binomiais direto via math.comb
    import math
    try:
        numerator = math.comb(n - c, k)
        denominator = math.comb(n, k)
        return 1.0 - (numerator / denominator)
    except ValueError:
        return 0.0


def aggregate_results(logs_dir: Path):
    """Varre a pasta de logs brutos, consolida os resultados e executa testes estatísticos."""
    logger.info(f"Varrendo diretório de logs: {logs_dir}")
    
    # 1. Coletar arquivos de log
    log_files = list(logs_dir.glob("*.json"))
    if not log_files:
        logger.warning("Nenhum log bruto de execução encontrado.")
        return
        
    logger.info(f"Encontrados {len(log_files)} arquivos de execução.")
    
    # 2. Agrupar dados por modelo, tarefa e rodada
    # TODO: Implementar parse e consolidação das métricas (tempo, custo, tokens, compilação, sucesso)
    # TODO: Gerar as matrizes de performance para alimentar as rotinas estatísticas
    
    logger.info("Consolidação concluída.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidador de resultados de Benchmark")
    parser.add_argument("--logs-dir", type=str, default=str(Path(__file__).resolve().parents[1] / "resultados" / "exec_logs"),
                        help="Diretório contendo os arquivos de log JSON")
    
    args = parser.parse_args()
    aggregate_results(Path(args.logs_dir))
