"""Testes de `shared/memory/config.py` — gates explícitos (interruptor geral
e uso de Postgres).

A feature inteira vem desligada por padrão (precisa de
`AI4ES_MEMORY_ENABLED=true`); e, quando ligada, Postgres também precisa ser
opcional — uma URL preenchida sozinha não basta, precisa de
`AI4ES_MEMORY_USE_POSTGRES=true` também, senão cai pro Chroma local.
"""

import importlib


def _reload_config(monkeypatch):
    from shared.memory import config

    importlib.reload(config)
    return config


class TestMemoriaHabilitada:
    def test_flag_ausente_e_false(self, monkeypatch):
        monkeypatch.delenv("AI4ES_MEMORY_ENABLED", raising=False)
        config = _reload_config(monkeypatch)
        assert config.memoria_habilitada() is False

    def test_flag_vazia_e_false(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "")
        config = _reload_config(monkeypatch)
        assert config.memoria_habilitada() is False

    def test_flag_false_e_false(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "false")
        config = _reload_config(monkeypatch)
        assert config.memoria_habilitada() is False

    def test_flag_true_e_true(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "true")
        config = _reload_config(monkeypatch)
        assert config.memoria_habilitada() is True

    def test_flag_true_maiusculo_e_true(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "TRUE")
        config = _reload_config(monkeypatch)
        assert config.memoria_habilitada() is True

    def test_qualquer_outro_valor_e_false(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "1")
        config = _reload_config(monkeypatch)
        assert config.memoria_habilitada() is False


class TestUsarPostgres:
    def test_flag_ausente_e_false(self, monkeypatch):
        monkeypatch.delenv("AI4ES_MEMORY_USE_POSTGRES", raising=False)
        config = _reload_config(monkeypatch)
        assert config._usar_postgres() is False

    def test_flag_vazia_e_false(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "")
        config = _reload_config(monkeypatch)
        assert config._usar_postgres() is False

    def test_flag_false_e_false(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "false")
        config = _reload_config(monkeypatch)
        assert config._usar_postgres() is False

    def test_flag_true_e_true(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "true")
        config = _reload_config(monkeypatch)
        assert config._usar_postgres() is True

    def test_flag_true_maiusculo_e_true(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "TRUE")
        config = _reload_config(monkeypatch)
        assert config._usar_postgres() is True

    def test_qualquer_outro_valor_e_false(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "1")
        config = _reload_config(monkeypatch)
        assert config._usar_postgres() is False


class TestDatabaseUrl:
    def test_url_preenchida_sem_flag_e_ignorada(self, monkeypatch):
        """O caso central da decisão: URL sozinha não basta."""
        monkeypatch.delenv("AI4ES_MEMORY_USE_POSTGRES", raising=False)
        monkeypatch.setenv(
            "AI4ES_MEMORY_DATABASE_URL", "postgresql://user:pass@host:5432/db"
        )
        config = _reload_config(monkeypatch)
        assert config._database_url() is None

    def test_url_preenchida_com_flag_true_e_usada(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "true")
        monkeypatch.setenv(
            "AI4ES_MEMORY_DATABASE_URL", "postgresql://user:pass@host:5432/db"
        )
        config = _reload_config(monkeypatch)
        assert config._database_url() == "postgresql://user:pass@host:5432/db"

    def test_flag_true_sem_url_e_none(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "true")
        monkeypatch.delenv("AI4ES_MEMORY_DATABASE_URL", raising=False)
        config = _reload_config(monkeypatch)
        assert config._database_url() is None


class TestVectorStoreConfig:
    def test_sem_flag_usa_chroma(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AI4ES_MEMORY_USE_POSTGRES", raising=False)
        monkeypatch.setenv(
            "AI4ES_MEMORY_DATABASE_URL", "postgresql://user:pass@host:5432/db"
        )
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        config = _reload_config(monkeypatch)
        assert config._vector_store_config()["provider"] == "chroma"

    def test_com_flag_true_usa_pgvector(self, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_USE_POSTGRES", "true")
        monkeypatch.setenv(
            "AI4ES_MEMORY_DATABASE_URL", "postgresql://user:pass@host:5432/db"
        )
        config = _reload_config(monkeypatch)
        assert config._vector_store_config()["provider"] == "pgvector"
