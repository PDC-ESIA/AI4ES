"""
test_validador.py
=================
Testes unitários para o módulo validador.py.

Cobertura
---------
- extrair_diff_codigo(): comportamento com diff vazio, com diff válido e com
  falha do subprocesso.
- Lógica de veredito: APROVADO, REPROVADO, ERRO e resposta inconclusiva.
- Integração assíncrona: garante que Runner.run_async() é chamado com os
  parâmetros corretos e que o texto da resposta final é extraído.

Execução
--------
    uv run python -m pytest test_validador.py -v
"""

import asyncio
import sys
import types as builtins_types
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Garante que o diretório adk/ está no path (necessário ao rodar testes isolados)
sys.path.insert(0, str(Path(__file__).parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_evento_final(texto: str):
    """Cria um objeto mock que simula um evento de resposta final do ADK."""
    parte = MagicMock()
    parte.text = texto

    conteudo = MagicMock()
    conteudo.parts = [parte]

    evento = MagicMock()
    evento.is_final_response.return_value = True
    evento.content = conteudo
    return evento


def _criar_evento_intermediario():
    """Cria um evento mock que NÃO é resposta final (deve ser ignorado)."""
    evento = MagicMock()
    evento.is_final_response.return_value = False
    return evento


async def _async_gen(*eventos):
    """Gerador assíncrono auxiliar que emite os eventos fornecidos."""
    for e in eventos:
        yield e


# ---------------------------------------------------------------------------
# Testes de extrair_diff_codigo
# ---------------------------------------------------------------------------


class TestExtrairDiffCodigo(unittest.TestCase):

    def _importar_extrair_diff(self):
        """Importa a função sem executar o bloco __main__."""
        import importlib
        import validador as mod

        importlib.reload(mod)
        return mod.extrair_diff_codigo

    @patch("subprocess.run")
    @patch.dict("os.environ", {"GITHUB_BASE_REF": "main"})
    def test_retorna_diff_quando_sucesso(self, mock_run):
        """Deve retornar o stdout do git diff quando returncode == 0."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="diff --git a/x b/x\n+linha nova"
        )
        import validador

        resultado = validador.extrair_diff_codigo()
        self.assertIn("+linha nova", resultado)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch.dict("os.environ", {"GITHUB_BASE_REF": "develop"})
    def test_usa_github_base_ref(self, mock_run):
        """Deve usar GITHUB_BASE_REF para construir o alvo do git diff."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        import validador

        validador.extrair_diff_codigo()
        args_chamada = mock_run.call_args[0][0]
        self.assertIn("origin/develop", args_chamada)

    @patch("subprocess.run")
    def test_usa_main_como_fallback(self, mock_run):
        """Deve usar 'main' quando GITHUB_BASE_REF não estiver definida."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        import os

        os.environ.pop("GITHUB_BASE_REF", None)
        import validador

        validador.extrair_diff_codigo()
        args_chamada = mock_run.call_args[0][0]
        self.assertIn("origin/main", args_chamada)

    @patch("subprocess.run")
    def test_encerra_processo_quando_git_falha(self, mock_run):
        """Deve chamar sys.exit(1) quando git diff retornar código de erro."""
        mock_run.return_value = MagicMock(
            returncode=128, stdout="", stderr="fatal: not a git repo"
        )
        import validador

        with self.assertRaises(SystemExit) as ctx:
            validador.extrair_diff_codigo()
        self.assertEqual(ctx.exception.code, 1)


# ---------------------------------------------------------------------------
# Testes da lógica de veredito (função main)
# ---------------------------------------------------------------------------


class TestLogicaVeredito(unittest.IsolatedAsyncioTestCase):
    """Testa o fluxo completo de main() usando mocks para o Runner e SessionService."""

    def _mock_runner_com_resposta(self, texto_resposta: str):
        """Configura mocks do Runner e SessionService retornando `texto_resposta`."""
        evento_final = _criar_evento_final(texto_resposta)
        evento_intermediario = _criar_evento_intermediario()

        runner_mock = MagicMock()
        runner_mock.run_async = MagicMock(
            return_value=_async_gen(evento_intermediario, evento_final)
        )

        session_mock = MagicMock()
        session_mock.id = "sessao-teste-123"

        session_service_mock = MagicMock()
        session_service_mock.create_session = AsyncMock(return_value=session_mock)

        return runner_mock, session_service_mock

    async def _executar_main_com_diff(self, diff: str, texto_resposta: str):
        """Executa validador.main() com o diff e resposta fornecidos, retornando o exit code."""
        runner_mock, session_service_mock = self._mock_runner_com_resposta(
            texto_resposta
        )

        import validador

        with patch("validador.extrair_diff_codigo", return_value=diff), patch(
            "validador.Runner", return_value=runner_mock
        ), patch(
            "validador.InMemorySessionService", return_value=session_service_mock
        ), patch(
            "sys.stdout", new_callable=StringIO
        ):
            try:
                await validador.main()
            except SystemExit as e:
                return e.code
        return None

    async def test_aprovado_retorna_exit_0(self):
        """Resposta com 'APROVADO' deve resultar em exit(0)."""
        codigo = await self._executar_main_com_diff(
            diff="+ def nova_funcao(): pass",
            texto_resposta="O código segue boas práticas.\nSTATUS: APROVADO",
        )
        self.assertEqual(codigo, 0)

    async def test_reprovado_retorna_exit_1(self):
        """Resposta com 'REPROVADO' deve resultar em exit(1)."""
        codigo = await self._executar_main_com_diff(
            diff="+ import *",
            texto_resposta="O código tem problemas graves.\nSTATUS: REPROVADO",
        )
        self.assertEqual(codigo, 1)

    async def test_erro_na_resposta_retorna_exit_1(self):
        """Resposta contendo 'ERRO' deve resultar em exit(1) por segurança."""
        codigo = await self._executar_main_com_diff(
            diff="+ algum codigo",
            texto_resposta="ERRO ao processar a análise.",
        )
        self.assertEqual(codigo, 1)

    async def test_resposta_inconclusiva_retorna_exit_1(self):
        """Resposta sem APROVADO/REPROVADO/ERRO deve bloquear por segurança."""
        codigo = await self._executar_main_com_diff(
            diff="+ algum codigo",
            texto_resposta="Não consegui determinar o status do PR.",
        )
        self.assertEqual(codigo, 1)

    async def test_diff_vazio_retorna_exit_0(self):
        """Diff vazio deve pular a validação e retornar exit(0)."""
        import validador

        with patch("validador.extrair_diff_codigo", return_value="   \n  "), patch(
            "sys.stdout", new_callable=StringIO
        ):
            try:
                await validador.main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
                return
        self.fail("Esperava SystemExit(0) para diff vazio")

    async def test_exception_no_runner_retorna_exit_1(self):
        """Exceção inesperada durante a execução do agente deve resultar em exit(1)."""
        import validador

        runner_mock = MagicMock()
        runner_mock.run_async = MagicMock(side_effect=Exception("Timeout de rede"))

        session_mock = MagicMock()
        session_mock.id = "sessao-erro"

        session_service_mock = MagicMock()
        session_service_mock.create_session = AsyncMock(return_value=session_mock)

        with patch(
            "validador.extrair_diff_codigo", return_value="+ codigo valido"
        ), patch("validador.Runner", return_value=runner_mock), patch(
            "validador.InMemorySessionService", return_value=session_service_mock
        ), patch(
            "sys.stdout", new_callable=StringIO
        ):
            try:
                await validador.main()
            except SystemExit as e:
                self.assertEqual(e.code, 1)
                return
        self.fail("Esperava SystemExit(1) quando Runner levanta exceção")

    async def test_eventos_intermediarios_sao_ignorados(self):
        """Eventos não-finais não devem contribuir para o veredito."""
        import validador

        evento_intermediario = _criar_evento_intermediario()
        evento_final = _criar_evento_final("STATUS: APROVADO")

        runner_mock = MagicMock()
        runner_mock.run_async = MagicMock(
            return_value=_async_gen(
                evento_intermediario, evento_intermediario, evento_final
            )
        )

        session_mock = MagicMock()
        session_mock.id = "sessao-intermediario"

        session_service_mock = MagicMock()
        session_service_mock.create_session = AsyncMock(return_value=session_mock)

        with patch("validador.extrair_diff_codigo", return_value="+ codigo ok"), patch(
            "validador.Runner", return_value=runner_mock
        ), patch(
            "validador.InMemorySessionService", return_value=session_service_mock
        ), patch(
            "sys.stdout", new_callable=StringIO
        ):
            try:
                await validador.main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
                return
        self.fail("Esperava SystemExit(0)")


# ---------------------------------------------------------------------------
# Testes do Runner sendo chamado com os parâmetros corretos
# ---------------------------------------------------------------------------


class TestParametrosRunner(unittest.IsolatedAsyncioTestCase):

    async def test_runner_recebe_app_name_correto(self):
        """O Runner deve ser instanciado com APP_NAME == 'agents'."""
        import validador

        evento_final = _criar_evento_final("APROVADO")
        runner_mock = MagicMock()
        runner_mock.run_async = MagicMock(return_value=_async_gen(evento_final))

        runner_class_mock = MagicMock(return_value=runner_mock)

        session_mock = MagicMock()
        session_mock.id = "s1"
        session_service_mock = MagicMock()
        session_service_mock.create_session = AsyncMock(return_value=session_mock)

        with patch("validador.extrair_diff_codigo", return_value="+ x = 1"), patch(
            "validador.Runner", runner_class_mock
        ), patch(
            "validador.InMemorySessionService", return_value=session_service_mock
        ), patch(
            "sys.stdout", new_callable=StringIO
        ):
            try:
                await validador.main()
            except SystemExit:
                pass

        _, kwargs = runner_class_mock.call_args
        self.assertEqual(kwargs.get("app_name"), "agents")

    async def test_run_async_recebe_session_id_correto(self):
        """run_async deve ser chamado com o session.id gerado pelo SessionService."""
        import validador

        evento_final = _criar_evento_final("APROVADO")
        runner_mock = MagicMock()
        runner_mock.run_async = MagicMock(return_value=_async_gen(evento_final))

        session_mock = MagicMock()
        session_mock.id = "sessao-especifica-xyz"
        session_service_mock = MagicMock()
        session_service_mock.create_session = AsyncMock(return_value=session_mock)

        with patch("validador.extrair_diff_codigo", return_value="+ x = 1"), patch(
            "validador.Runner", return_value=runner_mock
        ), patch(
            "validador.InMemorySessionService", return_value=session_service_mock
        ), patch(
            "sys.stdout", new_callable=StringIO
        ):
            try:
                await validador.main()
            except SystemExit:
                pass

        _, kwargs = runner_mock.run_async.call_args
        self.assertEqual(kwargs.get("session_id"), "sessao-especifica-xyz")


if __name__ == "__main__":
    unittest.main(verbosity=2)
