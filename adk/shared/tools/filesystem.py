"""Ferramentas de filesystem compartilhadas entre agentes."""

import re
from pathlib import Path

from .artifacts import registrar_markdown_artifact

EXTENSOES_PERMITIDAS = {
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".csv",
}

NOMES_PERMITIDOS = {".env.example"}

DIRETORIOS_PROIBIDOS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
}

ID_REQ_PATTERN = re.compile(r"^[A-Z]{1,4}-\d{3}$")


def _erro(caminho: str | None, mensagem: str) -> dict:
    return {
        "sucesso": False,
        "caminho": caminho,
        "bytes_escritos": 0,
        "erro": mensagem,
    }


def _caminho_relativo_seguro(caminho: str) -> tuple[Path | None, dict | None]:
    caminho_limpo = (caminho or "").strip()
    if not caminho_limpo:
        return None, _erro(caminho_limpo, "Caminho vazio não permitido.")

    path_relativo = Path(caminho_limpo)
    if path_relativo.is_absolute():
        return None, _erro(caminho_limpo, "Caminho absoluto não permitido.")

    if ".." in path_relativo.parts:
        return None, _erro(caminho_limpo, "Caminho com '..' não permitido.")

    partes = {parte.lower() for parte in path_relativo.parts}
    bloqueados = partes & DIRETORIOS_PROIBIDOS
    if bloqueados:
        return None, _erro(caminho_limpo, "Escrita em diretório protegido não permitida.")

    if (
        path_relativo.suffix.lower() not in EXTENSOES_PERMITIDAS
        and path_relativo.name not in NOMES_PERMITIDOS
    ):
        return None, _erro(
            caminho_limpo,
            f"Extensão não permitida: {path_relativo.suffix or '<sem extensão>'}.",
        )

    raiz = Path.cwd().resolve()
    path_final = (raiz / path_relativo).resolve()
    if path_final != raiz and raiz not in path_final.parents:
        return None, _erro(caminho_limpo, "Caminho fora do diretório permitido.")

    return path_final, None


def tool_criar_arquivo(caminho: str, conteudo: str) -> dict:
    """Cria ou sobrescreve um arquivo com validações de segurança."""
    path_final, erro = _caminho_relativo_seguro(caminho)
    if erro:
        return erro

    try:
        path_final.parent.mkdir(parents=True, exist_ok=True)
        path_final.write_text(conteudo, encoding="utf-8")
        return {
            "sucesso": True,
            "caminho": str(path_final),
            "bytes_escritos": len(conteudo.encode("utf-8")),
            "erro": None,
        }
    except Exception as e:
        return _erro(str(path_final), f"Erro ao criar arquivo: {e}")


def tool_salvar_relatorio(
    conteudo: str,
    nome_arquivo: str = "doubt_artifact_revisao.md",
) -> dict:
    """Salva um relatório Markdown no diretório de trabalho atual."""
    if not nome_arquivo.endswith(".md"):
        return _erro(nome_arquivo, "O relatório deve ser um arquivo Markdown (.md).")
    return tool_criar_arquivo(nome_arquivo, conteudo)


def tool_ler_arquivo(caminho: str) -> str:
    """Lê o conteúdo de um arquivo existente no disco."""
    try:
        path = Path(caminho)
        if not path.is_file():
            return f"Erro: O arquivo '{caminho}' não existe ou não é um arquivo válido."
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro inesperado ao ler o arquivo '{caminho}': {str(e)}"


def tool_substituir_trecho(caminho: str, trecho_antigo: str, trecho_novo: str) -> str:
    """Substitui um trecho existente por outro em um arquivo."""
    try:
        path = Path(caminho)
        if not path.is_file():
            return f"Erro: O arquivo '{caminho}' não existe. Use tool_criar_arquivo para criar arquivos novos."

        content = path.read_text(encoding="utf-8")
        if trecho_antigo not in content:
            return (
                f"Erro: 'trecho_antigo' não foi encontrado da maneira exata "
                f"que você informou no arquivo '{caminho}'."
            )

        path.write_text(content.replace(trecho_antigo, trecho_novo, 1), encoding="utf-8")
        return f"Sucesso: O bloco de código foi substituído no arquivo '{caminho}'."
    except Exception as e:
        return f"Erro inesperado ao editar o arquivo '{caminho}': {str(e)}"


async def tool_salvar_artefato_requisito(
    tipo: str,
    id_req: str,
    conteudo_md: str,
    tool_context=None,
) -> str:
    """Salva artefatos de requisito em Markdown com validação de ID."""
    mapa_pastas = {
        "HU": "docs/Time_1_Requisitos/HUs",
        "RF": "docs/Time_1_Requisitos/RFs",
        "RNF": "docs/Time_1_Requisitos/RNFs",
        "RN": "docs/Time_1_Requisitos/RNs",
        "UC": "docs/Time_1_Requisitos/UCs",
        "GLOSSARIO": "docs/Time_1_Requisitos",
    }

    tipo_normalizado = (tipo or "").strip().upper()
    id_req_normalizado = (id_req or "").strip()
    pasta_base = mapa_pastas.get(tipo_normalizado, "docs/Time_1_Requisitos/Outros")

    try:
        if tipo_normalizado != "GLOSSARIO" and not ID_REQ_PATTERN.fullmatch(id_req_normalizado):
            return "ERRO ao salvar artefato: id_req inválido. Use o padrão AAAA-999."

        nome_arquivo = (
            f"{id_req_normalizado}.md"
            if tipo_normalizado != "GLOSSARIO"
            else "Glossario.md"
        )
        pasta_base_path = Path(pasta_base).resolve()
        caminho_completo = (pasta_base_path / nome_arquivo).resolve()

        if caminho_completo.parent != pasta_base_path:
            return "ERRO ao salvar artefato: caminho de saída inválido."

        pasta_base_path.mkdir(parents=True, exist_ok=True)
        caminho_completo.write_text(conteudo_md, encoding="utf-8")
        artifact = await registrar_markdown_artifact(
            tool_context,
            Path(pasta_base) / nome_arquivo,
            conteudo_md,
        )
        if artifact["registrado"]:
            return (
                f"SUCESSO: {tipo_normalizado} {id_req_normalizado} salvo em {caminho_completo}. "
                f"Artifact ADK registrado como {artifact['filename']} v{artifact['versao']}."
            )

        return (
            f"SUCESSO: {tipo_normalizado} {id_req_normalizado} salvo em {caminho_completo}. "
            f"Artifact ADK não registrado: {artifact['erro']}"
        )
    except Exception as e:
        return f"ERRO ao salvar artefato: {str(e)}"
