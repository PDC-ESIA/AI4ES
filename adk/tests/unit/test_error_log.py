"""Testes do log local de erros brutos (PoC de memória em lote, sem Postgres)."""

import importlib


def _reload_error_log(tmp_path, monkeypatch):
    monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
    from shared.memory import error_log

    importlib.reload(error_log)
    return error_log


class TestArquivoStackSanitiza:
    """`_arquivo_stack` — sanitização contra path traversal / subpastas quebradas.

    `stack_key` vem de texto livre gerado por LLM (pode conter "/", "..").
    """

    def test_barra_vira_traco_nao_cria_subpasta(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        caminho = error_log._arquivo_stack("Python/FastAPI/SQLAlchemy")
        assert caminho.parent == error_log._dir_error_log()
        assert caminho.name == "python-fastapi-sqlalchemy.jsonl"

    def test_dois_pontos_nao_escapa_diretorio(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        caminho = error_log._arquivo_stack("../../etc/passwd")
        assert caminho.parent == error_log._dir_error_log()
        assert ".." not in caminho.name

    def test_string_vazia_apos_sanitizar_usa_fallback(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        caminho = error_log._arquivo_stack("///...")
        assert caminho.name == "stack-desconhecida.jsonl"

    def test_registrar_com_chave_suja_funciona_de_ponta_a_ponta(
        self, tmp_path, monkeypatch
    ):
        """Regressão: sem sanitizar, isso quebrava com FileNotFoundError
        (subpasta "python/fastapi/" nunca era criada)."""
        error_log = _reload_error_log(tmp_path, monkeypatch)
        error_log.registrar_erros("Python/FastAPI", [{"stage": "a"}])
        assert error_log.ler_erros_pendentes("Python/FastAPI") == [{"stage": "a"}]


class TestRegistrarELer:
    def test_sem_arquivo_retorna_lista_vazia(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        assert error_log.ler_erros_pendentes("python") == []

    def test_registra_e_le_de_volta(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        entradas = [{"stage": "a", "error_code": "X"}]
        error_log.registrar_erros("python", entradas)
        assert error_log.ler_erros_pendentes("python") == entradas

    def test_chamadas_sucessivas_acumulam(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        error_log.registrar_erros("python", [{"stage": "a"}])
        error_log.registrar_erros("python", [{"stage": "b"}])
        pendentes = error_log.ler_erros_pendentes("python")
        assert len(pendentes) == 2

    def test_stacks_diferentes_nao_se_misturam(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        error_log.registrar_erros("python", [{"stage": "a"}])
        error_log.registrar_erros("node", [{"stage": "b"}])
        assert len(error_log.ler_erros_pendentes("python")) == 1
        assert len(error_log.ler_erros_pendentes("node")) == 1

    def test_registrar_lista_vazia_nao_cria_entradas(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        error_log.registrar_erros("python", [])
        assert error_log.ler_erros_pendentes("python") == []


class TestLimparErrosPendentes:
    def test_limpa_arquivo_existente(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        error_log.registrar_erros("python", [{"stage": "a"}])
        error_log.limpar_erros_pendentes("python")
        assert error_log.ler_erros_pendentes("python") == []

    def test_limpar_sem_arquivo_nao_gera_erro(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        error_log.limpar_erros_pendentes("stack-nunca-usada")


class TestLimiteLote:
    def test_default_e_tres(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        monkeypatch.delenv("AI4ES_MEMORY_BATCH_THRESHOLD", raising=False)
        assert error_log.limite_lote() == 3

    def test_respeita_override_por_env_var(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "5")
        assert error_log.limite_lote() == 5

    def test_valor_vazio_usa_default(self, tmp_path, monkeypatch):
        """Regressão: `.env` costuma deixar a chave presente e vazia, não
        ausente — `int("")` quebrava a run inteira antes desse teste existir."""
        error_log = _reload_error_log(tmp_path, monkeypatch)
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "")
        assert error_log.limite_lote() == 3

    def test_valor_so_espacos_usa_default(self, tmp_path, monkeypatch):
        error_log = _reload_error_log(tmp_path, monkeypatch)
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "   ")
        assert error_log.limite_lote() == 3
