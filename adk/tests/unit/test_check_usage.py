"""Testes unitários para scripts/check_usage.py."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts.check_usage import check, get_daily_usage


def _make_generation(input_tokens: int, output_tokens: int):
    return SimpleNamespace(usage=SimpleNamespace(input=input_tokens, output=output_tokens))


def _make_generation_no_usage():
    return SimpleNamespace(usage=None)


class TestGetDailyUsage:
    def test_sums_tokens_across_pages(self):
        page1 = SimpleNamespace(data=[_make_generation(100, 50), _make_generation(200, 100)])
        page2 = SimpleNamespace(data=[_make_generation(300, 150)])
        page3 = SimpleNamespace(data=[])

        client = MagicMock()
        client.fetch_generations.side_effect = [page1, page2, page3]

        total = get_daily_usage(client)
        assert total == 100 + 50 + 200 + 100 + 300 + 150  # 900

    def test_handles_no_data(self):
        client = MagicMock()
        client.fetch_generations.return_value = SimpleNamespace(data=[])

        assert get_daily_usage(client) == 0

    def test_skips_none_usage(self):
        page = SimpleNamespace(data=[_make_generation(100, 50), _make_generation_no_usage()])
        empty = SimpleNamespace(data=[])

        client = MagicMock()
        client.fetch_generations.side_effect = [page, empty]

        assert get_daily_usage(client) == 150


class TestCheck:
    def test_returns_false_without_env_vars(self, monkeypatch):
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        assert check() is False

    @patch("scripts.check_usage.Langfuse")
    @patch("scripts.check_usage.get_daily_usage", return_value=500_000)
    def test_ok_below_threshold(self, mock_usage, mock_langfuse_cls, monkeypatch):
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
        monkeypatch.setenv("DAILY_TOKEN_LIMIT", "1000000")

        assert check(threshold=0.8) is True

    @patch("scripts.check_usage.Langfuse")
    @patch("scripts.check_usage.get_daily_usage", return_value=850_000)
    def test_alert_above_threshold(self, mock_usage, mock_langfuse_cls, monkeypatch):
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
        monkeypatch.setenv("DAILY_TOKEN_LIMIT", "1000000")

        assert check(threshold=0.8) is False

    @patch("scripts.check_usage.Langfuse")
    @patch("scripts.check_usage.get_daily_usage", return_value=1_100_000)
    def test_critical_at_limit(self, mock_usage, mock_langfuse_cls, monkeypatch, caplog):
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
        monkeypatch.setenv("DAILY_TOKEN_LIMIT", "1000000")

        with caplog.at_level(logging.CRITICAL):
            result = check(threshold=0.8)

        assert result is False
        assert any("LIMITE" in r.message for r in caplog.records)
