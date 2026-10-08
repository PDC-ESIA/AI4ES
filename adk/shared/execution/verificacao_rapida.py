"""Verificação rápida do artefato do coder, antes do harness completo.

Na run do fotógrafo, a TASK-001 gastou 4 iterações inteiras (~1 mi de tokens
cada: coder + build + subida + pytest + validador) com erros que um
`python -c "import app.main"` revelaria em segundos: módulo removido da stdlib,
import circular, símbolo importado do pacote errado, `TestClient` sem `httpx`.

Dois modos, escolhidos pela trilha (`shared.execution.trilhas`):

- **Com trilha** (stack conhecida, interpretador fixado): checagens
  determinísticas num venv em cache por hash de interpretador + dependências +
  restrições — `compileall`, import do módulo do `run`, coleta do pytest.
  Depois da 1ª instalação, cada verificação leva poucos segundos.
- **Sem trilha** (stack livre): uma revisão por LLM, barata, que lista erros
  prováveis de import/inicialização. Só bloqueia com confiança alta; qualquer
  falha da própria revisão deixa o harness seguir (nunca trava a task).

O resultado não aprova nada: só decide se vale a pena gastar o harness agora.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from shared.execution.manifest import ManifestError, RunManifest, load_manifest
from shared.execution.sandbox import DirectSandbox, _clean_env
from shared.execution.trilhas import ambiente_da_trilha

logger = logging.getLogger(__name__)

_TIMEOUT_INSTALACAO = 300
_TIMEOUT_CHECAGEM = 60
_MAX_SAIDA = 3000
_PASTAS_IGNORADAS = r"(^|/)(venv|\.venv|node_modules|\.ai4se_trilha|__pycache__)/"

# Revisão por LLM (stacks sem trilha)
_MAX_CHARS_REVISAO = 40_000
_EXTENSOES_CODIGO = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".go", ".java", ".kt", ".rb",
    ".php", ".rs", ".cs", ".html", ".json", ".toml", ".txt", ".xml", ".gradle",
}


@dataclass
class Falha:
    etapa: str
    detalhe: str
    comando: Optional[str] = None

    def como_texto(self) -> str:
        cabecalho = f"[{self.etapa}]" + (f" $ {self.comando}" if self.comando else "")
        return f"{cabecalho}\n{self.detalhe}".strip()


@dataclass
class ResultadoVerificacao:
    modo: str  # "trilha" | "genai" | "nenhum"
    falhas: list[Falha] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.falhas


def _cauda(texto: str, limite: int = _MAX_SAIDA) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= limite else "…" + texto[-limite:]


def _raiz_cache() -> Path:
    bruto = os.environ.get("AI4ES_VERIFICACAO_RAPIDA_CACHE", "").strip()
    return Path(bruto) if bruto else Path.home() / ".cache" / "ai4se" / "verificacao_rapida"


def _manifesto_de_dependencias(workdir: Path) -> Optional[Path]:
    alvo = workdir / "requirements.txt"
    return alvo if alvo.is_file() else None


def _chave_venv(interpretador: str, requisitos: Optional[Path], constraints: Optional[str]) -> str:
    h = hashlib.sha256(interpretador.encode())
    for caminho in (requisitos, Path(constraints) if constraints else None):
        if caminho is not None and caminho.is_file():
            h.update(caminho.read_bytes())
    return h.hexdigest()[:16]


def _venv_em_cache(
    trilha: dict, workdir: Path
) -> tuple[Optional[Path], Optional[Falha]]:
    """Python de um venv com as dependências do projeto (reaproveitado por hash)."""
    interpretador = trilha["interpretador"]
    constraints = trilha.get("constraints")
    requisitos = _manifesto_de_dependencias(workdir)
    destino = _raiz_cache() / _chave_venv(interpretador, requisitos, constraints)
    python = destino / "bin" / "python"
    if python.is_file():
        return python, None

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = Path(tempfile.mkdtemp(prefix=".venv-", dir=destino.parent))
    env = _clean_env({"PIP_CONSTRAINT": constraints} if constraints else None)
    try:
        proc = subprocess.run(
            [interpretador, "-m", "venv", str(temporario)],
            capture_output=True, text=True, timeout=_TIMEOUT_CHECAGEM, env=env,
        )
        if proc.returncode != 0:
            return None, Falha("ambiente", _cauda(proc.stderr or proc.stdout))
        if requisitos is not None:
            comando = [str(temporario / "bin" / "pip"), "install", "-q", "-r", str(requisitos)]
            proc = subprocess.run(
                comando, capture_output=True, text=True,
                timeout=_TIMEOUT_INSTALACAO, env=env, cwd=str(workdir),
            )
            if proc.returncode != 0:
                return None, Falha(
                    "dependencias",
                    _cauda(proc.stderr or proc.stdout),
                    comando="pip install -r requirements.txt",
                )
        try:
            os.replace(temporario, destino)
        except OSError:
            # Outra verificação concorrente gravou o mesmo venv primeiro.
            shutil.rmtree(temporario, ignore_errors=True)
        return python, None
    except subprocess.TimeoutExpired:
        return None, Falha("dependencias", "instalação excedeu o tempo limite")
    finally:
        if temporario.exists() and temporario != destino:
            shutil.rmtree(temporario, ignore_errors=True)


def modulo_de_entrada(manifest: RunManifest) -> Optional[str]:
    """Módulo importável que o `run` sobe (`app.main` de `uvicorn app.main:app`)."""
    run = manifest.run or ""
    achado = re.search(r"(?:^|\s)-m\s+([\w.]+)", run)
    if achado and achado.group(1) not in {"uvicorn", "gunicorn", "flask", "hypercorn"}:
        return achado.group(1)
    achado = re.search(r"([A-Za-z_][\w.]*):[A-Za-z_]\w*", run)
    if achado and ("uvicorn" in run or "gunicorn" in run or "hypercorn" in run):
        return achado.group(1)
    return None


def _tem_modulo(sandbox: DirectSandbox, py: str, modulo: str, env: dict) -> bool:
    res = sandbox.exec(f"{py} -c 'import {modulo}'", timeout=_TIMEOUT_CHECAGEM, env=env)
    return res.exit_code == 0


def _verificar_com_trilha(coder_dir: Path, manifest: RunManifest, trilha: dict) -> ResultadoVerificacao:
    resultado = ResultadoVerificacao(modo="trilha")
    workdir = (coder_dir / manifest.workdir).resolve()
    python, falha = _venv_em_cache(trilha, workdir)
    if falha is not None:
        resultado.falhas.append(falha)
        return resultado

    sandbox = DirectSandbox(workdir_subpath=manifest.workdir)
    try:
        sandbox.setup(coder_dir)
        env = {**ambiente_da_trilha(trilha, sandbox.root), **(manifest.env or {})}
        py = str(python)

        etapas: list[tuple[str, str, set[int]]] = [
            ("sintaxe", f"{py} -m compileall -q -x '{_PASTAS_IGNORADAS}' .", {0}),
        ]
        modulo = modulo_de_entrada(manifest)
        if modulo:
            etapas.append(
                ("import", f"{py} -c 'import importlib; importlib.import_module(\"{modulo}\")'", {0})
            )
        if any("pytest" in cmd for cmd in manifest.test) and _tem_modulo(sandbox, py, "pytest", env):
            # 5 = nenhum teste coletado; não é erro de importação. Sem pytest
            # declarado nas dependências, quem reporta é o harness.
            etapas.append(("coleta_de_testes", f"{py} -m pytest --collect-only -q", {0, 5}))

        for etapa, comando, aceitos in etapas:
            res = sandbox.exec(comando, timeout=_TIMEOUT_CHECAGEM, env=env)
            if res.timed_out:
                resultado.falhas.append(Falha(etapa, "tempo limite excedido", comando=comando))
                break
            if res.exit_code not in aceitos:
                saida = "\n".join(p for p in (res.stdout, res.stderr) if p)
                resultado.falhas.append(Falha(etapa, _cauda(saida), comando=comando.replace(py, "python")))
                break
    finally:
        sandbox.cleanup()
    return resultado


def executar_arquivo_de_teste(
    coder_dir: Path, trilha: Optional[dict], arquivo_rel: str
) -> tuple[Optional[int], str]:
    """Roda UM arquivo pytest contra o código atual, no venv em cache da trilha.

    Usado pelo autor de testes de aceite para conferir o próprio teste antes
    de entregá-lo: na validação, um teste com `allow_redirects` (API do
    requests, não do httpx) reprovou os 3 critérios de uma task sem que o
    código chegasse a ser avaliado. Devolve (exit_code, saída); exit_code None
    quando não há como rodar (sem trilha, sem manifesto, sem pytest).
    """
    if not (isinstance(trilha, dict) and trilha.get("interpretador")):
        return None, "Execução indisponível: a stack não está numa trilha conhecida."
    try:
        manifest = load_manifest(coder_dir / "run.json")
    except ManifestError as exc:
        return None, f"Execução indisponível: run.json inválido ({exc})."
    workdir = (coder_dir / manifest.workdir).resolve()
    python, falha = _venv_em_cache(trilha, workdir)
    if falha is not None:
        return None, f"Execução indisponível: {falha.como_texto()}"
    sandbox = DirectSandbox(workdir_subpath=manifest.workdir)
    try:
        sandbox.setup(coder_dir)
        env = {**ambiente_da_trilha(trilha, sandbox.root), **(manifest.env or {})}
        if not _tem_modulo(sandbox, str(python), "pytest", env):
            return None, "Execução indisponível: pytest não está nas dependências do projeto."
        res = sandbox.exec(
            f"{python} -m pytest -v -p no:cacheprovider -p no:warnings --tb=short -rfE {arquivo_rel}",
            timeout=120,
            env=env,
        )
    finally:
        sandbox.cleanup()
    saida = "\n".join(p for p in (res.stdout, res.stderr) if p)
    return (None if res.timed_out else res.exit_code), _cauda(saida, 3500)


# ── Revisão por LLM (sem trilha) ──────────────────────────────────────────

_PROMPT_REVISAO = """Você é um revisor de build. Abaixo está um projeto gerado por \
outro agente (stack: {stack}). Ele vai ser construído e executado com o \
manifesto `run.json`. Liste SOMENTE erros que certamente impedem o build, a \
importação ou a inicialização: dependência importada mas não declarada, \
módulo/símbolo inexistente, import circular, caminho do `run` que não existe, \
sintaxe inválida. NÃO comente estilo, testes ou lógica de negócio.

Responda APENAS um JSON: {{"erros": [{{"arquivo": "...", "descricao": "...", \
"confianca": "alta|media|baixa"}}]}}. Lista vazia se não houver.

{arquivos}"""


def _coletar_arquivos(coder_dir: Path) -> str:
    partes: list[str] = []
    total = 0
    candidatos = sorted(
        (p for p in coder_dir.rglob("*") if p.is_file()),
        key=lambda p: (p.name != "run.json", p.stat().st_size),
    )
    for caminho in candidatos:
        rel = caminho.relative_to(coder_dir).as_posix()
        if re.search(_PASTAS_IGNORADAS, rel) or caminho.suffix not in _EXTENSOES_CODIGO:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        bloco = f"--- {rel} ---\n{texto}\n"
        if total + len(bloco) > _MAX_CHARS_REVISAO:
            break
        partes.append(bloco)
        total += len(bloco)
    return "".join(partes)


def _chamar_llm(prompt: str) -> str:
    from litellm import completion

    from shared.llm import copilot_completion_kwargs
    from shared.token_usage import record_litellm_response

    modelo = (
        os.environ.get("AI4ES_VERIFICACAO_RAPIDA_MODELO", "").strip()
        or os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")
    )
    kwargs = copilot_completion_kwargs(modelo)
    if "/" not in modelo:
        modelo = f"gemini/{modelo}"
        kwargs["api_key"] = os.environ.get("GOOGLE_API_KEY")
    resposta = completion(
        model=modelo, messages=[{"role": "user", "content": prompt}], **kwargs
    )
    record_litellm_response(resposta, agent="verificacao_rapida")
    return resposta.choices[0].message.content or ""


def _interpretar_revisao(texto: str) -> list[Falha]:
    achado = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if not achado:
        return []
    try:
        dados = json.loads(achado.group(0))
    except ValueError:
        return []
    falhas = []
    for erro in dados.get("erros") or []:
        if not isinstance(erro, dict) or str(erro.get("confianca", "")).lower() != "alta":
            continue
        arquivo = str(erro.get("arquivo") or "?")
        falhas.append(Falha("revisao_llm", f"{arquivo}: {erro.get('descricao', '')}".strip()))
    return falhas


def _verificar_por_llm(coder_dir: Path, stack: str) -> ResultadoVerificacao:
    resultado = ResultadoVerificacao(modo="genai")
    arquivos = _coletar_arquivos(coder_dir)
    if not arquivos:
        return resultado
    try:
        texto = _chamar_llm(_PROMPT_REVISAO.format(stack=stack or "não informada", arquivos=arquivos))
    except Exception:  # noqa: BLE001 — a revisão nunca trava a task
        logger.warning("[VERIFICACAO_RAPIDA] revisão por LLM indisponível", exc_info=True)
        return resultado
    resultado.falhas = _interpretar_revisao(texto)
    return resultado


def verificar_rapido(
    coder_dir: Path, trilha: Optional[dict], *, stack: str = ""
) -> ResultadoVerificacao:
    """Checa o artefato do coder; `ok` quando nada impede o harness de valer a pena."""
    try:
        manifest = load_manifest(coder_dir / "run.json")
    except ManifestError:
        # O gate de executabilidade já recusa manifesto inválido.
        return ResultadoVerificacao(modo="nenhum")
    if isinstance(trilha, dict) and trilha.get("interpretador"):
        return _verificar_com_trilha(coder_dir, manifest, trilha)
    return _verificar_por_llm(coder_dir, stack)
