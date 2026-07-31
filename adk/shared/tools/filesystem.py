"""Ferramentas de filesystem compartilhadas entre agentes (requisitos + workspace genérico).

As tools exclusivas do fluxo de codificação (tool_criar_arquivo,
tool_ler_arquivo, tool_substituir_trecho, tool_salvar_relatorio) vivem em
shared/tools/coding_review/filesystem.py.
"""

import re
from pathlib import Path
from typing import Optional

from shared.tools._path_utils import _resolver_caminho

ID_REQ_PATTERN = re.compile(r"^[A-Z]{1,4}-\d{3}$")

# Layout legado: paths absolutos baseados no CWD.
_PASTAS_LEGADO = {
    "HU": "docs/Time_1_Requisitos/HUs",
    "RF": "docs/Time_1_Requisitos/RFs",
    "RNF": "docs/Time_1_Requisitos/RNFs",
    "RN": "docs/Time_1_Requisitos/RNs",
    "GLOSSARIO": "docs/Time_1_Requisitos",
}

# Layout relativo a base_dir (workspace-bound): apenas o subdir.
_SUBPASTAS_BASE_DIR = {
    "HU": "HUs",
    "RF": "RFs",
    "RNF": "RNFs",
    "RN": "RNs",
    "GLOSSARIO": "",  # vai direto na raiz do base_dir
}


def tool_salvar_artefato_requisito(
    tipo: str,
    id_req: str,
    conteudo_md: str,
    base_dir: Optional[str] = None,
) -> str:
    """Persiste um artefato estruturado de requisito (HU, RF, RNF, RN, Glossário).

    Use ao final da análise de cada requisito atômico para gravar o
    artefato em Markdown no subdiretório canônico do tipo. O subdiretório
    é escolhido automaticamente pelo `tipo`. IDs (exceto Glossário)
    seguem o padrão AAAA-999 (ex: HU-001, RF-002).

    Args:
        tipo: Tipo do artefato. Valores aceitos (case-insensitive): HU,
            RF, RNF, RN, GLOSSARIO. Outros tipos vão para "Outros".
        id_req: Identificador do requisito (regex `^[A-Z]{1,4}-\\d{3}$`,
            ex: HU-001, RF-002, RNF-003). Não se aplica a GLOSSARIO,
            cujo arquivo é fixo "Glossario.md".
        conteudo_md: Texto Markdown completo do artefato.
        base_dir: Diretório base do agente. Quando informado, escreve
            em `<base_dir>/<subdir>/<id_req>.md`. Quando None, usa o
            caminho legado relativo ao CWD.

    Returns:
        str com mensagem "SUCESSO: <tipo> <id> salvo em <caminho>" em
        sucesso, ou "ERRO ao salvar artefato: <motivo>" em falha
        (id_req fora do padrão, path inválido, I/O).
    """
    tipo_normalizado = (tipo or "").strip().upper()
    id_req_normalizado = (id_req or "").strip()

    if tipo_normalizado != "GLOSSARIO":
        if not ID_REQ_PATTERN.fullmatch(id_req_normalizado):
            return "ERRO ao salvar artefato: id_req inválido. Use o padrão AAAA-999."

    nome_arquivo = (
        f"{id_req_normalizado}.md"
        if tipo_normalizado != "GLOSSARIO"
        else "Glossario.md"
    )

    try:
        if base_dir is None:
            # Caminho legado (CWD-relativo)
            pasta_base = _PASTAS_LEGADO.get(
                tipo_normalizado, "docs/Time_1_Requisitos/Outros"
            )
            pasta_base_path = Path(pasta_base).resolve()
            pasta_base_path.mkdir(parents=True, exist_ok=True)
            caminho_completo = (pasta_base_path / nome_arquivo).resolve()

            if (
                caminho_completo.parent != pasta_base_path
                and pasta_base_path not in caminho_completo.parents
            ):
                return "ERRO ao salvar artefato: caminho de saída inválido."
        else:
            # Caminho workspace-bound
            subdir = _SUBPASTAS_BASE_DIR.get(tipo_normalizado, "Outros")
            caminho_rel = f"{subdir}/{nome_arquivo}" if subdir else nome_arquivo
            caminho_completo = _resolver_caminho(caminho_rel, base_dir)
            caminho_completo.parent.mkdir(parents=True, exist_ok=True)

        caminho_completo.write_text(conteudo_md, encoding="utf-8")
        return f"SUCESSO: {tipo} {id_req} salvo em {caminho_completo}"
    except ValueError as e:
        return f"ERRO ao salvar artefato: {str(e)}"
    except Exception as e:
        return f"ERRO ao salvar artefato: {str(e)}"


def tool_ler_workspace(caminho: str, base_dir: Optional[str] = None) -> str:
    """Lê arquivo de qualquer subpasta do workspace global (cross-agent, read-only).

    Diferente da capacidade de leitura escopada ao agente, esta permite
    que um agente consulte outputs gerados por outros agentes — ex:
    reviewer/qa consultam o que o coder produziu. Não permite escrita
    em workspace de outro agente.

    Args:
        caminho: Caminho relativo à raiz do workspace global
            (ex: 'coder/main.py').
        base_dir: Raiz do workspace (injetada pela factory como
            workspace_root). Obrigatório — sem ele a tool retorna erro.

    Returns:
        str com o conteúdo do arquivo, ou string "Erro:" descrevendo
        path traversal, arquivo inexistente ou base_dir ausente.
    """
    if base_dir is None:
        return "Erro: tool_ler_workspace requer base_dir (raiz do workspace)."

    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return f"Erro: {e}"

    if not path.is_file():
        return f"Erro: arquivo '{caminho}' não existe em {base_dir}."

    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro ao ler '{caminho}': {e}"


def tool_listar_workspace(caminho: str = ".", base_dir: Optional[str] = None) -> str | list[str]:
    """Lista os arquivos e diretórios de um caminho do workspace global.

    Use para descobrir o que outros agentes produziram antes de
    consultar arquivos individuais com a capacidade de leitura.
    Retorna nomes ordenados alfabeticamente.

    Args:
        caminho: Caminho relativo à raiz do workspace (default ".",
            que lista a raiz).
        base_dir: Raiz do workspace (injetada pela factory).
            Obrigatório.

    Returns:
        list[str] com nomes em ordem alfabética, ou str "Erro:" se
        diretório inexistente, path traversal ou base_dir ausente.
    """
    if base_dir is None:
        return "Erro: tool_listar_workspace requer base_dir (raiz do workspace)."

    try:
        path = _resolver_caminho(caminho, base_dir)
    except ValueError as e:
        return f"Erro: {e}"

    if not path.is_dir():
        return f"Erro: diretório '{caminho}' não existe em {base_dir}."

    try:
        return sorted(p.name for p in path.iterdir())
    except Exception as e:
        return f"Erro ao listar '{caminho}': {e}"
