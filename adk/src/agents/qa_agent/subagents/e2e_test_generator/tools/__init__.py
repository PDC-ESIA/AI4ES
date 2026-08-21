"""Operações determinísticas que compõem o P0 E2E."""

from .analisar_superficie_sistema import analisar_superficie_sistema
from .gerar_testes_e2e import gerar_testes_e2e
from .gerar_playwright_spec import gerar_playwright_spec, renderizar_playwright_spec
from .inspecionar_projeto_e2e import inspecionar_projeto_e2e
from .executar_playwright import executar_playwright
from .mapear_cenarios_e2e import mapear_cenarios_e2e
from .normalizar_entrada_e2e import normalizar_entrada_e2e
from .obter_plano_acao import obter_plano_acao
from .validar_contrato_e2e import validar_contrato_e2e

__all__ = [
    "analisar_superficie_sistema",
    "gerar_testes_e2e",
    "gerar_playwright_spec",
    "executar_playwright",
    "inspecionar_projeto_e2e",
    "mapear_cenarios_e2e",
    "normalizar_entrada_e2e",
    "obter_plano_acao",
    "renderizar_playwright_spec",
    "validar_contrato_e2e",
]
