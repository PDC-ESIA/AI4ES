"""Imagem Docker de avaliação do BigCodeBench (build sob demanda).

O código gerado por LLM importa bibliotecas de terceiros, então roda num
container (nunca no ambiente do dev). A imagem é construída uma vez a partir de
`sandbox/Dockerfile` e reutilizada nos runs seguintes.
"""

from __future__ import annotations

from pathlib import Path

from .dataset import DEFAULT_HF_VERSION

IMAGE_TAG = f"ai4se-bigcodebench-sandbox:{DEFAULT_HF_VERSION}"
_SANDBOX_DIR = Path(__file__).resolve().parent / "sandbox"


def ensure_image(tag: str = IMAGE_TAG, *, rebuild: bool = False) -> str:
    """Garante que a imagem `tag` exista localmente, construindo-a se preciso.

    Raises:
        RuntimeError: se o daemon do Docker não estiver acessível.
    """
    import docker
    from docker.errors import DockerException, ImageNotFound

    try:
        client = docker.from_env()
        client.ping()
    except DockerException as exc:
        raise RuntimeError(
            "Docker indisponível: inicie o Docker (Desktop/daemon) — o BigCodeBench "
            f"executa o código gerado num container isolado. Detalhe: {exc}"
        ) from exc

    if not rebuild:
        try:
            client.images.get(tag)
            return tag
        except ImageNotFound:
            pass

    print(f"[sandbox] Construindo imagem {tag} (pode levar vários minutos)…")
    _, logs = client.images.build(path=str(_SANDBOX_DIR), tag=tag, rm=True)
    for entrada in logs:
        linha = (entrada.get("stream") or "").strip()
        if linha:
            print(f"[sandbox] {linha}")
    return tag
