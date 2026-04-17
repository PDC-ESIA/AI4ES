import pytest
import textwrap
from pathlib import Path

from adk.agents.roles.qa_agent.tools.pytest_runner import executar_pytest_tool, _contador_execucoes, MAX_TENTATIVAS

@pytest.fixture
def setup_ambiente_teste(tmp_path):
    def _criar_arquivo_teste(nome_arquivo: str, conteudo: str) -> str:
        caminho_arquivo = tmp_path / nome_arquivo
        caminho_arquivo.write_text(conteudo, encoding="utf-8")
        return str(caminho_arquivo)
    return _criar_arquivo_teste

def test_auditoria_sucesso_cobertura(setup_ambiente_teste):
    # Usando dedent para garantir que as funções fiquem encostadas na margem esquerda
    conteudo_teste_sucesso = textwrap.dedent("""
    def soma(a, b): return a + b
    def test_soma(): 
        assert soma(2, 2) == 4
    """).strip()
    
    caminho_teste = setup_ambiente_teste("test_sucesso.py", conteudo_teste_sucesso)
    resultado = executar_pytest_tool(caminho_teste)

    assert resultado["status"] == "sucesso"
    assert resultado["agente_origem"] == "pytest_runner"
    assert resultado["proxima_acao_orquestrador"] == "finalizar_qa"
    assert "cobertura" in resultado
    assert resultado["cobertura"]["percentual"] > 0.0

def test_auditoria_trigger_roteamento_falha(setup_ambiente_teste):
    conteudo_teste_falha = textwrap.dedent("""
    def test_falha_esperada(): 
        assert 2 + 2 == 5
    """).strip()
    
    caminho_teste = setup_ambiente_teste("test_falha.py", conteudo_teste_falha)
    resultado = executar_pytest_tool(caminho_teste)

    assert resultado["status"] == "falha"
    assert resultado["proxima_acao_orquestrador"] == "trigger_correcao_matunag"
    assert len(resultado["erros"]) > 0
    assert "ERR_TESTE_FALHOU" in resultado["erros"][0]["codigo"]
    assert "assert 2 + 2 == 5" in resultado["erros"][0]["log"]

def test_auditoria_trava_de_loop(setup_ambiente_teste):
    conteudo_teste = "def test_dummy(): assert False"
    caminho_teste = setup_ambiente_teste("test_loop_infinito.py", conteudo_teste)
    
    _contador_execucoes[caminho_teste] = MAX_TENTATIVAS + 1
    resultado = executar_pytest_tool(caminho_teste)

    assert resultado["status"] == "falha"
    assert resultado["erros"][0]["codigo"] == "ERR_LOOP"
    
    dir_doubt = Path(caminho_teste).parent / "doubt_artifacts"
    assert dir_doubt.exists()
    
    arquivos_doubt = list(dir_doubt.glob("*.md"))
    assert len(arquivos_doubt) == 1
    assert "test_loop_infinito" in arquivos_doubt[0].name