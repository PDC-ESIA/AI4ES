"""
design_filesystem.py
─────────────
Camada de persistência usada exclusivamente pelo Agente IO.
Responsabilidade: ler, salvar, promover e listar artefatos em disco.

Logging de operações delegado integralmente ao IOLogger (design_logger.py).
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .design_logger import IOLogger

def _find_root(start_path: Path, target: str = "adk") -> Path:
    for parent in start_path.parents:
        if parent.name == target:
            return parent
    return start_path.parents[4]  # Fallback seguro (Atualizar se necessário)

ADK_DIR = _find_root(Path(__file__).resolve())
DESIGN_DIR = ADK_DIR / "workspace_output" / "design"

ANALYSIS_DIR = DESIGN_DIR / "analysis"
DIAGRAMS_DIR = DESIGN_DIR / "diagrams"
PROTOTYPE_DIR = DESIGN_DIR / "prototypes"
REPORT_DIR = DESIGN_DIR / "reports"
DOUBT_DIR = DESIGN_DIR / "doubts"
OFFICIAL_DIR = DESIGN_DIR / "entrega_final" # Sujeito a mudanças
LOCKS_DIR = DESIGN_DIR / ".locks"

TEMPLATE_DIR = ADK_DIR / "shared" / "templates"
LOG_FILENAME = "io_operations.log"
STATUS_IN_REVIEW = "**Status:** Em análise"
STATUS_BLOCKED = "**Status:** Bloqueado"
BACKUP_PREFIX = "_backup_"
_SECTION_SEPARATOR = "\n<<<FIM_SECAO>>>\n"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers Privados
# ──────────────────────────────────────────────────────────────────────────────

def _resolve_dirs(base_dir: str | None = None) -> Dict[str, Path]:
    """
    Resolve o conjunto de diretórios de design usado por uma chamada.

    Sem base_dir (default — comportamento histórico preservado): usa a raiz
    fixa e compartilhada DESIGN_DIR (workspace_output/design), a mesma para
    todos os agentes do pipeline.

    Com base_dir: trata o valor como a raiz de um workspace isolado — por
    exemplo, o agent_workspace injetado via closure por
    shared/agent_factory.py quando create_se_agent(..., agent_subdir=...) é
    usado — e recria a mesma estrutura de subpastas (analysis/, diagrams/,
    prototypes/, reports/, doubts/, entrega_final/) dentro dele.

    ⚠️  templates NUNCA são escopados por base_dir — são sempre lidos do
    TEMPLATE_DIR global do projeto.
    """
    root = Path(base_dir).resolve() if base_dir else DESIGN_DIR
    return {
        "root": root,
        "analysis": root / "analysis",
        "diagrams": root / "diagrams",
        "prototype": root / "prototypes",
        "report": root / "reports",
        "doubt": root / "doubts",
        "official": root / "entrega_final",
        "template": TEMPLATE_DIR,
        "validation": root / "validation",
    }


def _safety_root(base_dir: str | None = None) -> Path:
    """
    Raiz usada para validar que nenhuma leitura/escrita escapa da área
    permitida (ver _is_safe_path). Sem base_dir, a área permitida é todo o
    projeto (ADK_DIR) — comportamento histórico. Com base_dir, a área
    permitida é restrita ao próprio workspace isolado — verificação MAIS
    estrita, nunca mais permissiva.
    """
    return Path(base_dir).resolve() if base_dir else ADK_DIR.resolve()


def _ensure_dirs(dirs: Dict[str, Path]) -> None:
    for key in ("analysis", "diagrams", "prototype", "report", "doubt", "official"):
        dirs[key].mkdir(parents=True, exist_ok=True)


def _is_safe_path(path: Path, root: Path) -> bool:
    """
    True se `path` está dentro de `root`, OU dentro de TEMPLATE_DIR.

    TEMPLATE_DIR é uma exceção deliberada e fixa: templates são globais e
    nunca escopados por base_dir (ver docstring de _resolve_dirs). Sem esta
    exceção aqui, qualquer leitura de template feita por um agente com
    workspace isolado (root = base_dir do agente, não o projeto inteiro)
    seria rejeitada como "fora do projeto" mesmo usando o alias correto —
    já aconteceu na prática após a integração com agent_factory.
    """
    try:
        resolved_path = path.resolve()
        if resolved_path.is_relative_to(root):
            return True
        return resolved_path.is_relative_to(TEMPLATE_DIR.resolve())
    except (ValueError, RuntimeError):
        return False


def _next_version(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.parent / f"{path.stem}{BACKUP_PREFIX}{timestamp}{path.suffix}"


# Nomes exibidos nas mensagens de erro — apenas os canônicos, legível para o agente.
_FOLDER_ALIAS_DISPLAY = (
    "ANALYSIS, ANALYSIS_DIR, ANALYSIS_FOLDER, "
    "DIAGRAMS, DIAGRAMS_DIR, DIAGRAMS_FOLDER, "
    "PROTOTYPE, PROTOTYPE_DIR, PROTOTYPE_FOLDER, "
    "REPORT, REPORT_DIR, REPORT_FOLDER, "
    "DOUBT, DOUBT_DIR, DOUBT_FOLDER, "
    "TEMPLATE_DIR, TEMPLATE_FOLDER"
)


def _folder_aliases(dirs: Dict[str, Path]) -> Dict[str, Path]:
    """Mapa de aliases simbólicos → diretório canônico, para um `dirs` já resolvido."""
    return {
        # ANALYSIS
        "analysis":         dirs["analysis"],
        "analysis_dir":     dirs["analysis"],
        "analysis_folder":  dirs["analysis"],
        # DIAGRAMS
        "diagrams":         dirs["diagrams"],
        "diagrams_dir":     dirs["diagrams"],
        "diagrams_folder":  dirs["diagrams"],
        # PROTOTYPE
        "prototype":        dirs["prototype"],
        "prototype_dir":    dirs["prototype"],
        "prototype_folder": dirs["prototype"],
        # REPORT
        "report":           dirs["report"],
        "report_dir":       dirs["report"],
        "report_folder":    dirs["report"],
        # DOUBT
        "doubt":            dirs["doubt"],
        "doubt_dir":        dirs["doubt"],
        "doubt_folder":     dirs["doubt"],
        # templates
        "template":         dirs["template"],
        "template_dir":     dirs["template"],
        "template_folder":  dirs["template"],
    }


def _resolve_folder_alias(token: str, dirs: Dict[str, Path]) -> "tuple[Path | None, str | None]":
    """
    Converte um token simbólico de pasta no Path absoluto correspondente,
    dentro do `dirs` resolvido para esta chamada (ver _resolve_dirs).

    Retorna (Path, None) se o alias for reconhecido, ou (None, mensagem_de_erro)
    se o token não estiver no mapa. Token vazio retorna (None, None) — sem erro,
    sem pasta; o chamador usa a lógica padrão (busca em ANALYSIS→DIAGRAMS→PROTOTYPE).
    """
    if not token:
        return None, None
    resolved = _folder_aliases(dirs).get(token.lower().strip())
    if resolved is not None:
        return resolved, None
    error = (
        f"Pasta '{token}' não reconhecida. "
        f"Pastas disponíveis: {_FOLDER_ALIAS_DISPLAY}."
    )
    return None, error


def _split_folder_and_name(raw: str) -> "tuple[str, str]":
    """
    Separa um token de pasta de um nome de arquivo em `raw`.

    Exemplos:
        "REPORT/relatorio.md"    → ("REPORT",    "relatorio.md")
        "relatorio.md"           → ("",           "relatorio.md")
        "PROTOTYPE/"             → ("PROTOTYPE",  "")
    """
    normalized = raw.strip().replace("\\", "/")
    if "/" not in normalized:
        return "", normalized
    prefix, rest = normalized.split("/", 1)
    return prefix, rest.strip("/")


def _strip_redundant_alias_segments(filename: str, dirs: Dict[str, Path]) -> str:
    """
    Remove segmentos de pasta redundantes do INÍCIO de `filename` que já
    correspondem a um alias de pasta conhecido — ex.: "diagrams/x.mmd" → "x.mmd",
    "diagrams/diagrams/x.mmd" → "x.mmd", "DIAGRAMS/diagrams/x.mmd" → "x.mmd".

    Por quê: existem hoje duas camadas que podem decidir prefixar o nome do
    arquivo com o alias da pasta de destino — o agente que descreve o pedido
    em linguagem natural (ex.: "salve na pasta de diagramas") e o Agente IO,
    que por convenção própria monta literalmente "DIAGRAMS/<nome>" antes de
    chamar esta ferramenta. Se as duas camadas prefixarem o mesmo nome, o
    resultado sem esta função seria salvar em <pasta>/<pasta>/<nome> — um
    arquivo fisicamente válido, mas invisível para qualquer listagem que só
    enxerga o primeiro nível da pasta oficial (foi exatamente o que aconteceu
    com os diagramas .mmd de uma run real, salvos em
    design/diagrams/diagrams/ em vez de design/diagrams/ — o
    markdown_specialist e o validator reportaram DIAGRAMS/ vazia e bloquearam
    o pipeline achando que os diagramas nunca tinham sido gerados).

    Esta função torna a resolução de caminho IDEMPOTENTE em relação a esse
    prefixo: não importa quantas vezes um alias de pasta apareça no início do
    nome, o destino final é sempre o mesmo único nível dentro da pasta.
    """
    aliases = set(_folder_aliases(dirs).keys())
    current = filename
    while True:
        token, rest = _split_folder_and_name(current)
        if token and rest and token.lower().strip() in aliases:
            current = rest
            continue
        break
    return current


def _resolve_path_arg(raw: str, dirs: Dict[str, Path]) -> "tuple[Path | None, str, str | None]":
    """
    Ponto único de resolução para qualquer argumento de caminho vindo do agente.

    Aceita:
        "relatorio.md"              → busca em ANALYSIS→DIAGRAMS→PROTOTYPE
        "ANALYSIS/relatorio.md"     → dirs["analysis"],  "relatorio.md",  sem erro
        "PROTOTYPE/login.html"      → dirs["prototype"], "login.html",    sem erro
        "spec/algo.md"              → None,               "algo.md",      mensagem de erro
        "DIAGRAMS/diagrams/x.mmd"   → dirs["diagrams"],   "x.mmd",         sem erro
                                       (prefixo duplicado é removido — ver
                                       _strip_redundant_alias_segments)

    Retorna:
        (resolved_dir, clean_filename, error_msg)

        resolved_dir   — Path do diretório ou None (sem alias explícito).
        clean_filename — nome do arquivo sem prefixo de pasta (nunca contém
                          outro alias de pasta embutido — duplicatas já
                          foram removidas).
        error_msg      — None se ok; string se o prefixo não foi reconhecido.
    """
    folder_token, filename = _split_folder_and_name(raw)
    resolved_dir, error = _resolve_folder_alias(folder_token, dirs)
    if error:
        return resolved_dir, filename, error
    filename = _strip_redundant_alias_segments(filename, dirs)
    return resolved_dir, filename, error


def _find_existing_file(filename: str, dirs: Dict[str, Path], root: Path) -> "Path | None":
    """
    Procura `filename` em todas as pastas conhecidas do design (analysis,
    diagrams, prototype, report, doubt, validation, template — nesta ordem)
    e retorna o primeiro Path que existe. Retorna None se não encontrado em
    nenhuma delas.

    A ordem prioriza as pastas mais lidas sem alias (analysis/diagrams/
    prototype) primeiro, por desempenho — mas nenhuma pasta fica de fora.
    Isso evita falso "arquivo não encontrado" quando o chamador omite o
    alias de pasta para um arquivo que só existe em report/doubt/validation/
    template (já aconteceu na prática: relatorio_design_template.md existia
    em TEMPLATE_DIR mas não era encontrado por uma leitura sem o prefixo
    "TEMPLATE/", porque a busca padrão não cobria essa pasta).
    """
    for directory in (
        dirs["analysis"], dirs["diagrams"], dirs["prototype"],
        dirs["report"], dirs["doubt"], dirs["validation"], dirs["template"],
    ):
        candidate = (directory / filename).resolve()
        if _is_safe_path(candidate, root) and candidate.exists():
            return candidate
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Helpers Privados — Lock de Escrita
# ──────────────────────────────────────────────────────────────────────────────
#
# O lock é indexado pelo NOME do arquivo (alias de pasta é ignorado): o mesmo
# nome resolve sempre para o mesmo lock, independente de como o especialista
# referenciou a pasta. Locks vivem em LOCKS_DIR como arquivos JSON criados
# atomicamente (O_CREAT | O_EXCL) — dois especialistas nunca obtêm o mesmo lock.
# Leituras nunca consultam locks; apenas operações de escrita são controladas.


def _lock_path(filename: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return LOCKS_DIR / f"{safe_name}.lock"


def _read_lock(lock_file: Path) -> "Dict[str, Any] | None":
    """Retorna os metadados do lock ou None se o arquivo estiver livre."""
    try:
        return json.loads(lock_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        # Lock ilegível: trata como ocupado por dono desconhecido (conservador).
        return {"owner": "desconhecido", "acquired_at": ""}


def _check_write_permission(filename: str, caller: str | None) -> "Dict[str, Any] | None":
    """
    Valida se `caller` possui permissão de escrita (lock) sobre `filename`.

    Retorna None quando autorizado, ou um dict de erro pronto para ser
    devolvido ao agente quando a escrita deve ser bloqueada.
    """
    lock_info = _read_lock(_lock_path(filename))
    if lock_info is None:
        return {
            "status": "blocked",
            "error": (
                f"Escrita bloqueada: nenhum lock ativo para '{filename}'. "
                "Adquira permissão de escrita com acquire_lock (informando seu nome em caller) "
                "antes de modificar o arquivo e libere-o com release_lock ao terminar."
            ),
            "filename": filename,
        }
    owner = lock_info.get("owner", "desconhecido")
    if owner != (caller or ""):
        return {
            "status": "blocked",
            "error": (
                f"Escrita bloqueada: o arquivo '{filename}' está com lock de '{owner}'. "
                f"Somente '{owner}' pode modificá-lo até liberar o lock via release_lock."
            ),
            "filename": filename,
            "locked_by": owner,
        }
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Funções Públicas (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def read_file(filepath: str, caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Lê e retorna o conteúdo completo de um arquivo.

    O agente pode informar apenas o nome do arquivo ou prefixá-lo com um alias
    de pasta. Quando nenhum alias é fornecido, o sistema busca automaticamente
    em ANALYSIS → DIAGRAMS → PROTOTYPE e retorna o primeiro arquivo encontrado.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "relatorio_HU-001.md"
                            "STAGING/relatorio_HU-001.md"
                            "PROTOTYPE/login.html"
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        dict com chaves: `status` ("ok" | "error"), `content` (str
        UTF-8 em sucesso), `error` (str descritivo em falha — acesso
        negado, arquivo inexistente, erro de I/O).
    """
    try:
        dirs = _resolve_dirs(base_dir)
        root = _safety_root(base_dir)

        resolved_dir, filename, error = _resolve_path_arg(filepath, dirs)
        if error:
            return {"status": "error", "error": error}

        if resolved_dir is not None:
            # Alias explícito: olha só na pasta indicada
            path = (resolved_dir / filename).resolve()
            if not _is_safe_path(path, root):
                return {"status": "error", "error": "Acesso negado: caminho fora do projeto."}
            if not path.exists():
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em {resolved_dir.name}."}
        else:
            # Sem alias: busca em todas as pastas conhecidas
            path = _find_existing_file(filename, dirs, root)
            if path is None:
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida ({_FOLDER_ALIAS_DISPLAY})."}

        content = path.read_text(encoding="utf-8")
        IOLogger.read(path.name, caller=caller)
        return {"status": "ok", "content": content}

    except Exception as e:
        IOLogger.error("read_file", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def read_analysis_sections(filepath: str, sections: list[int], caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Lê seções específicas de um arquivo analise_tecnica_.md.

    O agente pode informar apenas o nome do arquivo ou prefixá-lo com um alias
    de pasta. Sem alias, busca automaticamente em ANALYSIS.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplo: "analise_tecnica_HU-001.md"
                           "ANALYSIS/analise_tecnica_HU-001.md"
        sections: Lista de números das seções desejadas. Exemplo: [4, 8]
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        Sucesso:  {"status": "ok",      "content": "<seções concatenadas>"}
        Aviso:    {"status": "warning", "content": "<arquivo completo>",
                   "msg": "Não foi possível extrair as seções. Retornando arquivo completo."}
        Falha:    {"status": "error",   "error":   "<motivo>"}
    """
    try:
        import re

        dirs = _resolve_dirs(base_dir)

        resolved_dir, filename, error = _resolve_path_arg(filepath, dirs)
        if error:
            return {"status": "error", "error": error}
        resolved_dir = dirs["analysis"]  # Sempre vai estar salvo em analysis_dir
        path = (resolved_dir / filename).resolve()

        content = path.read_text(encoding="utf-8")

        parts = re.split(r'<<<FIM_SECAO>>>', content)
        extracted = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            first_line = part.split('\n')[0].strip()
            match = re.match(r'^(\d+)\.', first_line)
            if match and int(match.group(1)) in sections:
                extracted.append(part)

        IOLogger.read(path.name + f" [sections:{sections}]", caller=caller)

        if not extracted:
            return {"status": "warning", "content": content, "msg": "Não foi possível extrair as seções solicitadas. Retornando arquivo completo."}

        return {"status": "ok", "content": "\n\n<<<FIM_SECAO>>>\n\n".join(extracted)}

    except Exception as e:
        IOLogger.error("read_analysis_sections", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def validate_analysis_sections(filename: str, caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Verifica DETERMINISTICAMENTE se um arquivo analise_tecnica_*.md contém as
    8 seções obrigatórias (1 a 8), cada uma separada por "<<<FIM_SECAO>>>" e
    com conteúdo além do título.

    Diferente de pedir a um agente para "ler o arquivo e conferir" — o que
    depende da interpretação do LLM e pode ser satisfeito por uma leitura
    superficial ou por um relato equivocado de conclusão — esta função aplica
    a MESMA lógica estrutural que read_analysis_sections() usa para separar
    seções, e reporta objetivamente quais números estão ausentes ou vazios.

    Use isto como o "portão" (gate) de conclusão do design_architect (fim do
    PASSO 8, antes do PASSO 9) e como a verificação de ETAPA 2 do
    pipeline_controller — em vez de confiar apenas na mensagem de confirmação
    do design_architect ou em uma leitura manual do conteúdo.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplo: "analise_tecnica_HU-001_HU-002.md"
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        Sucesso: {"status": "ok", "complete": bool,
                  "found_sections": [1, 2, ...],
                  "missing_sections": [<números ausentes>],
                  "empty_sections": [<números presentes mas sem conteúdo>],
                  "section_delimiter_count": <int>}
        Falha:   {"status": "error", "error": "<motivo>"}
    """
    import re

    _REQUIRED_SECTIONS = list(range(1, 9))

    try:
        dirs = _resolve_dirs(base_dir)
        root = _safety_root(base_dir)

        resolved_dir, fname, error = _resolve_path_arg(filename, dirs)
        if error:
            return {"status": "error", "error": error}

        if resolved_dir is not None:
            path = (resolved_dir / fname).resolve()
            if not _is_safe_path(path, root):
                return {"status": "error", "error": "Acesso negado: caminho fora do projeto."}
        else:
            path = _find_existing_file(fname, dirs, root)

        if path is None or not path.exists():
            return {"status": "error", "error": f"Arquivo '{fname}' não encontrado."}

        content = path.read_text(encoding="utf-8")
        parts = [p.strip() for p in content.split("<<<FIM_SECAO>>>") if p.strip()]

        found: Dict[int, str] = {}
        for part in parts:
            first_line = part.split("\n")[0].strip()
            match = re.match(r'^(\d+)\.', first_line)
            if not match:
                continue
            number = int(match.group(1))
            if number in _REQUIRED_SECTIONS and number not in found:
                body = part[len(first_line):].strip()
                found[number] = body

        missing = [n for n in _REQUIRED_SECTIONS if n not in found]
        empty = [n for n in _REQUIRED_SECTIONS if n in found and not found[n]]

        IOLogger.read(path.name + " [validate_analysis_sections]", caller=caller)

        return {
            "status": "ok",
            "complete": not missing and not empty,
            "found_sections": sorted(found.keys()),
            "missing_sections": missing,
            "empty_sections": empty,
            "section_delimiter_count": content.count("<<<FIM_SECAO>>>"),
        }

    except Exception as e:
        IOLogger.error("validate_analysis_sections", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def read_multiple_files(filepaths: list[str], caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Lê o conteúdo de vários arquivos em uma única chamada.

    Cada item da lista pode ser um nome simples ou conter um alias de pasta.
    Arquivos sem alias são buscados automaticamente em ANALYSIS → DIAGRAMS → PROTOTYPE.
    Arquivos não encontrados ou inacessíveis são reportados individualmente sem
    impedir a leitura dos demais.

    Args:
        filepaths: Lista de nomes de arquivo, com ou sem alias de pasta.
                   Exemplo: ["relatorio_HU-001.md", "PROTOTYPE/login.html"]
        caller:    Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir:  Raiz de workspace isolado (injetada via closure por
                   agent_factory quando aplicável). Sem base_dir, usa a
                   raiz compartilhada do projeto.

    Returns:
        Sucesso:  {"status": "ok", "contents": {
                      "<filepath>": {"status": "ok",    "content": "<conteúdo>"},
                      "<filepath>": {"status": "error", "error":   "<motivo>"},
                      ...
                  }}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        dirs = _resolve_dirs(base_dir)
        root = _safety_root(base_dir)

        contents = {}
        for raw in filepaths:
            resolved_dir, filename, error = _resolve_path_arg(raw, dirs)

            if error:
                contents[raw] = {"status": "error", "error": error}
                continue

            if resolved_dir is not None:
                path = (resolved_dir / filename).resolve()
                if not _is_safe_path(path, root):
                    contents[raw] = {"status": "error", "error": "Acesso negado: caminho fora do projeto."}
                    continue
                if not path.exists():
                    contents[raw] = {"status": "error", "error": f"Arquivo '{filename}' não encontrado em {resolved_dir.name}."}
                    continue
            else:
                path = _find_existing_file(filename, dirs, root)
                if path is None:
                    contents[raw] = {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida."}
                    continue

            contents[raw] = {"status": "ok", "content": path.read_text(encoding="utf-8")}

        file_types = {Path(f).suffix.lstrip('.').lower() for f in filepaths if '.' in f}
        str_file_types = ", ".join(file_types) if file_types else "sem extensão"

        IOLogger.read(f"[batch: {len(filepaths)} files | types: {str_file_types}]", caller=caller)
        return {"status": "ok", "contents": contents}

    except Exception as e:
        IOLogger.error("read_multiple_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def save_artifact(filename: str, content: str, caller: str | None = "unknown", base_dir: str | None = None) -> dict:
    """
    Salva um arquivo em uma das pastas do projeto. Se o arquivo já existir,
    cria backup automático antes de sobrescrever.

    O agente pode prefixar o nome com um alias de pasta para controlar o destino.
    Sem alias, .html e global.css vão para PROTOTYPE; .mmd vai para DIAGRAMS;
    os demais vão para ANALYSIS.

    ⚠️  Sobrescreve o arquivo inteiro. Para acrescentar conteúdo, use append_artifact.
    ⚠️  Para corrigir uma seção específica de Markdown, use patch_section.
    ⚠️  Requer lock de escrita: adquira-o antes com acquire_lock (informando seu nome
        em caller) e libere-o com release_lock ao terminar. Escrita sem lock, ou com
        lock pertencente a outro especialista, é bloqueada.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "relatorio_HU-001.md"
                            "ANALYSIS/relatorio_HU-001.md"
                            "PROTOTYPE/login.html"
        content:  Conteúdo completo do arquivo.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto (comportamento histórico).

    Returns:
        dict com chaves: `status` ("ok" | "blocked" | "error"), `path` (str do
        path final em sucesso), `versioned_backup` (str do path do
        backup criado, se houve; None caso contrário), `timestamp`
        (ISO 8601). Em bloqueio ou erro: `error`, `filename`.
    """
    try:
        dirs = _resolve_dirs(base_dir)
        root = _safety_root(base_dir)
        _ensure_dirs(dirs)

        resolved_dir, filename, error = _resolve_path_arg(filename, dirs)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        denied = _check_write_permission(filename, caller)
        if denied:
            IOLogger.error("save_artifact", denied["error"], caller=caller)
            return denied

        if resolved_dir is not None:
            target_dir = resolved_dir
        elif filename.startswith("Doubt_Artifact"):
            # Hardcoded de propósito: um Doubt_Artifact mal roteado fica
            # invisível para check_active_blocks, e isso já aconteceu mais
            # de uma vez (pasta errada, ou direto na raiz de design/). Não
            # dependemos do agente lembrar do alias "doubt_dir/" — o nome
            # do arquivo já é suficiente para rotear com segurança.
            target_dir = dirs["doubt"]
        elif filename.endswith(".html") or filename == "global.css":
            target_dir = dirs["prototype"]
        elif filename.endswith(".mmd"):
            target_dir = dirs["diagrams"]
        else:
            target_dir = dirs["analysis"]

        destination = (target_dir / filename).resolve()
        if not _is_safe_path(destination, root):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        destination.parent.mkdir(parents=True, exist_ok=True)

        versioned_backup = ""
        if destination.exists():
            backup_path = _next_version(destination)
            shutil.move(str(destination), str(backup_path))
            versioned_backup = str(backup_path)

        destination.write_text(content, encoding="utf-8")
        timestamp = datetime.now().isoformat()

        IOLogger.save(filename, caller=caller, backup=versioned_backup)

        return {
            "status": "ok",
            "path": str(destination),
            "versioned_backup": versioned_backup,
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("save_artifact", str(e), caller=caller)
        return {"status": "error", "error": str(e), "filename": filename}


def promote_artifact(filename: str, caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Copia um relatório aprovado para REPORT_DIR (diretório oficial permanente).

    Use somente quando o solicitante tiver alterado o status do relatório para "Aprovado"
    e pedir explicitamente a promoção. Nunca promova sem verificar o status antes.

    Restrições aplicadas automaticamente:
    - Apenas arquivos .md cujo nome contenha "relatorio" podem ser promovidos.
    - O arquivo deve conter "**Status:** Aprovado"; se ainda contiver "**Status:** Em análise",
      a promoção é bloqueada com status "blocked".
    - Diagramas .mmd, HTMLs, CSS e analise_tecnica_ nunca são promovidos.

    Args:
        filename: Nome do relatório. Apenas o nome — sem alias de pasta.
                  Exemplo: "relatorio_HU-001_HU-002.md"
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        dict com chaves: `status` ("ok" | "blocked" | "error"),
        `source`, `destination`, `timestamp` em sucesso; `reason` e
        `file` em "blocked"; `error` em "error".
    """
    try:
        dirs = _resolve_dirs(base_dir)
        root = _safety_root(base_dir)

        raw_filename = Path(filename)
        if raw_filename.is_absolute() or ".." in raw_filename.parts:
            raise PermissionError("Segurança: Caminho inválido.")

        source = _find_existing_file(raw_filename.name, dirs, root)
        if source is None:
            return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida."}

        if source.suffix != ".md":
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos. Diagramas .mmd permanecem em sua pasta de origem.",
                "file": filename,
            }

        if "relatorio" not in filename:
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos. A analise_tecnica_ permanece em sua pasta de origem.",
                "file": filename,
            }

        content = source.read_text(encoding="utf-8")
        if STATUS_IN_REVIEW in content:
            return {
                "status": "blocked",
                "reason": f"O relatório ainda possui o marcador '{STATUS_IN_REVIEW}'. Aprovação manual necessária.",
                "file": filename,
            }

        _ensure_dirs(dirs)
        destination = (dirs["official"] / raw_filename).resolve()
        if not _is_safe_path(destination, root):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        if destination.exists():
            shutil.move(str(destination), str(_next_version(destination)))

        shutil.copy2(str(source), str(destination))
        timestamp = datetime.now().isoformat()

        IOLogger.promote(filename, caller=caller)

        return {
            "status": "ok",
            "source": str(source),
            "destination": str(destination),
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("promote_artifact", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def list_design_files(filetype: str = "", folder: str = "", caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Lista os arquivos presentes em uma pasta do projeto.

    Sem `folder`, lista todas subpastas de design.
    Com `folder`, lista apenas a pasta indicada pelo alias.

    Backups (nomes com "_backup_") e o arquivo de log são ignorados automaticamente.

    Args:
        filetype: Extensão para filtrar, sem o ponto. Exemplos: "md", "html", "mmd".
                  Vazio = todos os arquivos.
        folder:   Alias da pasta a listar. Exemplos: "ANALYSIS", "PROTOTYPE", "DIAGRAMS".
                  Vazio = todas subpastas.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        Sucesso:  {"status": "ok", "files": ["arquivo1.md", ...],
                   "folder": "<alias canônico da pasta listada>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        dirs = _resolve_dirs(base_dir)
        _ensure_dirs(dirs)

        # Resolve alias de pasta, se fornecido
        target_dir, error = _resolve_folder_alias(folder, dirs)
        if error:
            return {"status": "error", "error": error}

        def _list_dir(directory: Path) -> list[str]:
            if not directory.exists():
                return []
            return [
                f.name
                for f in sorted(directory.iterdir())
                if f.is_file()
                and f.name != LOG_FILENAME
                and BACKUP_PREFIX not in f.name
                and (not filetype or f.suffix == f".{filetype}")
            ]

        if target_dir is not None:
            # Pasta explícita
            files = _list_dir(target_dir)
            folder_label = target_dir.name.upper()
        else:
            # Comportamento padrão: todas as subpastas de design
            files = _list_dir(dirs["analysis"]) + _list_dir(dirs["diagrams"]) + _list_dir(dirs["prototype"]) + _list_dir(dirs["report"])
            folder_label = "ANALYSIS+DIAGRAMS+PROTOTYPE+REPORT"

        IOLogger.read(f"[list:{filetype or 'all'} folder:{folder_label}]", caller=caller)
        return {
            "status": "ok",
            "files": sorted(list(set(files))),
            "folder": folder_label,
        }

    except Exception as e:
        IOLogger.error("list_design_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def check_active_blocks(caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Verifica se há Doubt_Artifacts com status "Bloqueado" em DOUBT_DIR.

    Use após receber retomada de um bloqueio, para confirmar que todos os
    Doubt_Artifacts foram realmente resolvidos antes de prosseguir o pipeline.

    Um Doubt_Artifact é considerado bloqueado se seu conteúdo contiver:
    "**Status:** Bloqueado". Após resolução, o solicitante deve alterar essa
    linha para "**Status:** Resolvido".

    Além do contrato canônico acima (mantido intacto), esta função agora
    também:
    (a) varre analysis/diagrams/prototype/report/validation além de
        doubts/ — Doubt_Artifacts salvos na pasta errada por um agente
        continuam sendo detectados como bloqueio;
    (b) reconhece o cabeçalho "EXECUÇÃO PAUSADA" como marcador de bloqueio
        equivalente a "**Status:** Bloqueado" — cobre Doubt_Artifacts que
        usam outra convenção de status (ex.: "Status: Pendente") mas que
        já se autodeclaram como pausa de execução.
    Isso é aditivo: nenhum caso que já era detectado deixa de ser.

    Args:
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        Sem bloqueios: {"status": "ok", "has_blocks": false, "blocks": []}
        Com bloqueios: {"status": "ok", "has_blocks": true,
                        "blocks": [{"filename": "<nome>", "hu_id": "<HU_ID>", "folder": "<pasta>"}, ...]}
        Falha:         {"status": "error", "error": "<motivo>"}
    """
    _BLOCK_MARKERS = (STATUS_BLOCKED, "EXECUÇÃO PAUSADA")
    _SCAN_FOLDERS = ("doubt", "analysis", "diagrams", "prototype", "report", "validation", "root")

    try:
        dirs = _resolve_dirs(base_dir)
        _ensure_dirs(dirs)
        blocks = []
        seen_paths: set[Path] = set()
        for folder_key in _SCAN_FOLDERS:
            folder_path = dirs.get(folder_key)
            if folder_path is None or not folder_path.exists():
                continue
            for f in sorted(folder_path.iterdir()):
                if not f.is_file():
                    continue
                if f.name.startswith("Doubt_Artifact") and BACKUP_PREFIX not in f.name:
                    resolved = f.resolve()
                    if resolved in seen_paths:
                        continue
                    seen_paths.add(resolved)
                    content = f.read_text(encoding="utf-8")
                    if any(marker in content for marker in _BLOCK_MARKERS):
                        parts = f.stem.split("_")
                        hu_id = parts[2] if len(parts) >= 3 else "desconhecido"
                        blocks.append({
                            "filename": f.name,
                            "hu_id": hu_id,
                            "folder": folder_key,
                        })

        IOLogger.read("[check_active_blocks]", caller=caller)
        return {"status": "ok", "has_blocks": len(blocks) > 0, "blocks": blocks}

    except Exception as e:
        IOLogger.error("check_active_blocks", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def clear_design_folder(caller: str | None = "unknown", base_dir: str | None = None) -> bool:
    """
    Remove todos os arquivos de DESIGN e seus subdiretórios.
    A estrutura de pastas é preservada — apenas os arquivos são deletados.

    Use exclusivamente no início de um novo ciclo do pipeline.
    Esta operação é irreversível — não há backup dos arquivos removidos.

    ⚠️  Nunca chame esta função no meio de uma execução ativa do pipeline.

    Args:
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        bool: True se todos os arquivos foram removidos com sucesso,
        False em caso de erro (ex: tentativa fora do diretório seguro, falha de I/O). Erros são registrados via IOLogger.
    """
    dirs = _resolve_dirs(base_dir)
    try:
        root = _safety_root(base_dir)
        _ensure_dirs(dirs)

        def _clear_recursive(directory: Path):
            if not _is_safe_path(directory, root):
                return
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    _clear_recursive(item)

        _clear_recursive(dirs["root"])
        IOLogger.erase(str(dirs["root"]), caller=caller)
        return True

    except Exception as e:
        IOLogger.error("ERASE", f"dir={dirs['root']} | error={str(e)}", caller=caller)
        return False


def append_artifact(filename: str, content: str, caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Adiciona conteúdo ao fim de um arquivo existente, sem apagar o que já está lá.
    Se o arquivo não existir, cria-o (comportamento idêntico ao save_artifact).

    O agente pode prefixar o nome com um alias de pasta. Sem alias, .html e
    global.css vão para PROTOTYPE; .mmd vai para DIAGRAMS; os demais vão para ANALYSIS.

    ⚠️  Não cria backup. Para substituir o arquivo inteiro, use save_artifact.
    ⚠️  Para corrigir uma seção já escrita, use patch_section.
    ⚠️  Requer lock de escrita: adquira-o antes com acquire_lock (informando seu nome
        em caller) e libere-o com release_lock ao terminar. Escrita sem lock, ou com
        lock pertencente a outro especialista, é bloqueada.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "analise_tecnica_HU-001.md"
                            "PROTOTYPE/login.html"
        content:  Trecho a ser adicionado ao fim do arquivo.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        Sucesso:  {"status": "ok", "path": "<caminho>",
                   "bytes_total": <tamanho total após append>, "timestamp": "<ISO 8601>"}
        Bloqueio: {"status": "blocked", "error": "<motivo>", "filename": "<nome>"}
        Falha:    {"status": "error", "error": "<motivo>", "filename": "<nome>"}
    """
    try:
        dirs = _resolve_dirs(base_dir)
        root = _safety_root(base_dir)
        _ensure_dirs(dirs)

        resolved_dir, filename, error = _resolve_path_arg(filename, dirs)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        denied = _check_write_permission(filename, caller)
        if denied:
            IOLogger.error("append_artifact", denied["error"], caller=caller)
            return denied

        if resolved_dir is not None:
            target_dir = resolved_dir
        elif filename.startswith("Doubt_Artifact"):
            target_dir = dirs["doubt"]
        elif filename.endswith(".html") or filename == "global.css":
            target_dir = dirs["prototype"]
        elif filename.endswith(".mmd"):
            target_dir = dirs["diagrams"]
        elif filename.startswith("relatorio_"):
            target_dir = dirs["report"]
        else:
            target_dir = dirs["analysis"]

        destination = (target_dir / filename).resolve()
        if not _is_safe_path(destination, root):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("a", encoding="utf-8") as f:
            f.write(content)

        bytes_total = destination.stat().st_size
        timestamp = datetime.now().isoformat()

        IOLogger.append(filename, caller=caller, bytes_added=len(content.encode()), bytes_total=bytes_total)

        return {
            "status": "ok",
            "path": str(destination),
            "bytes_total": bytes_total,
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("append_artifact", str(e), caller=caller)
        return {"status": "error", "error": str(e), "filename": filename}


def append_architect_section(filename: str, content: str, caller: str | None = "design_architect", base_dir: str | None = None) -> Dict[str, Any]:
    # A ideia inicial era fazer isso via prompt, mas estava instável e isso é essencial demais para ter qualquer instabilidade
    """
    Append exclusivo do design_architect.
    Adiciona conteúdo ao fim de um arquivo existente, sem apagar o que já está lá.
    Se o arquivo não existir, cria-o (comportamento idêntico ao save_artifact).

    ⚠️  Não cria backup. Para substituir o arquivo inteiro, use save_artifact.
    ⚠️  Para corrigir uma seção já escrita, use patch_section.

    Args:
        filename: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "analise_tecnica_HU-001.md"
                            "PROTOTYPE/login.html"
        content:  Trecho a ser adicionado ao fim do arquivo.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir: Raiz de workspace isolado (injetada via closure por
                  agent_factory quando aplicável). Sem base_dir, usa a
                  raiz compartilhada do projeto.

    Returns:
        Sucesso:  {"status": "ok", "path": "<caminho>",
                   "bytes_total": <tamanho total após append>, "timestamp": "<ISO 8601>"}
        Falha:    {"status": "error", "error": "<motivo>", "filename": "<nome>"}
    """
    # Remove token duplicado se o agente já incluiu (evita duplo marcador)
    normalized = content.rstrip("\n").removesuffix("<<<FIM_SECAO>>>").rstrip("\n")
    return append_artifact(filename, normalized + _SECTION_SEPARATOR, caller=caller, base_dir=base_dir)


def patch_section(filename: str, section_id: str, new_content: str, caller: str | None = "unknown", base_dir: str | None = None) -> Dict[str, Any]:
    """
    Substitui uma seção específica de um arquivo Markdown, sem alterar as demais.

    O agente pode prefixar o nome com um alias de pasta. Sem alias, o sistema
    busca o arquivo automaticamente em ANALYSIS → DIAGRAMS → PROTOTYPE.

    A seção é identificada de duas formas (primeiro match vence):
    - Por número isolado: section_id="4" encontra a seção cuja primeira linha começa com "4." ou "4 ".
    - Por heading Markdown exato: section_id="## Título".

    ⚠️  section_id deve ser APENAS o número ("4") ou o heading exato — nunca "4. Título".
    ⚠️  new_content deve incluir o título da seção, mas NUNCA um delimitador de
        fim de seção ("---" ou "<<<FIM_SECAO>>>") — o delimitador original do
        arquivo é preservado automaticamente. Se um for incluído por engano,
        é removido antes de gravar.
    ⚠️  Um backup automático é criado antes de qualquer alteração.
    ⚠️  Requer lock de escrita: adquira-o antes com acquire_lock (informando seu nome
        em caller) e libere-o com release_lock ao terminar. Escrita sem lock, ou com
        lock pertencente a outro especialista, é bloqueada.

    DELIMITADOR DE SEÇÃO — detectado automaticamente, nunca hardcoded:
    Esta ferramenta é genérica e pode ser chamada por qualquer agente sobre
    qualquer artefato Markdown do design (relatório, análise técnica, etc.) —
    cada tipo de arquivo pode usar uma convenção de separação diferente:
    - "---\\n" (horizontal rule Markdown): convenção de arquivos genéricos
      escritos via save_artifact/append_artifact (ex.: relatorio_*.md).
    - "<<<FIM_SECAO>>>\\n": convenção exclusiva de analise_tecnica_*.md,
      escrito via append_architect_section.
    patch_section identifica qual delimitador o arquivo já usa (podem até
    coexistir) e preserva exatamente esse delimitador ao regravar — nunca
    substitui um pelo outro. Isto corrige um bug anterior em que a regravação
    sempre forçava "---" mesmo em arquivos que usavam "<<<FIM_SECAO>>>",
    corrompendo o delimitador real do arquivo na primeira correção aplicada.

    Args:
        filename:    Nome do arquivo, com ou sem alias de pasta.
                     Exemplos: "analise_tecnica_HU-001.md"
                               "ANALYSIS/analise_tecnica_HU-001.md"
        section_id:  Número isolado ("4") ou heading Markdown exato ("## Título").
        new_content: Conteúdo completo da seção corrigida, incluindo título e "---" final.
        caller:      Nome do agente solicitante (usado apenas para rastreabilidade).
        base_dir:    Raiz de workspace isolado (injetada via closure por
                     agent_factory quando aplicável). Sem base_dir, usa a
                     raiz compartilhada do projeto.

    Returns:
        Sucesso:       {"status": "ok",      "path": "<caminho>", "section_found": true,
                        "backup": "<caminho do backup>", "timestamp": "<ISO 8601>"}
        Não encontrou: {"status": "warning", "section_found": false,
                        "error": "Seção '<id>' não encontrada. Arquivo não alterado.",
                        "hint": "Use read_analysis_sections para inspecionar os IDs disponíveis."}
        Falha:         {"status": "error",   "error": "<motivo>", "filename": "<nome>"}
    """
    try:
        import re
        dirs = _resolve_dirs(base_dir)
        root = _safety_root(base_dir)
        _ensure_dirs(dirs)

        resolved_dir, filename, error = _resolve_path_arg(filename, dirs)
        if error:
            return {"status": "error", "error": error, "filename": filename}

        denied = _check_write_permission(filename, caller)
        if denied:
            IOLogger.error("patch_section", denied["error"], caller=caller)
            return denied

        if resolved_dir is not None:
            destination = (resolved_dir / filename).resolve()
            if not _is_safe_path(destination, root):
                raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")
            if not destination.exists():
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em {resolved_dir.name}. Use save_artifact para criar."}
        else:
            destination = _find_existing_file(filename, dirs, root)
            if destination is None:
                return {"status": "error", "error": f"Arquivo '{filename}' não encontrado em nenhuma pasta conhecida. Use save_artifact para criar."}

        original = destination.read_text(encoding="utf-8")

        backup_path = _next_version(destination)
        shutil.copy2(str(destination), str(backup_path))

        # Captura o delimitador junto com o split (grupo de captura), em vez
        # de descartá-lo — assim ele pode ser preservado tal como estava no
        # arquivo, sem assumir qual dos dois formatos está em uso.
        parts = re.split(r'((?<=\n)(?:---|<<<FIM_SECAO>>>)\n)', original)

        _DELIMITER_TOKENS = {"---", "<<<FIM_SECAO>>>"}

        def _strip_trailing_delimiter(content: str) -> str:
            text = content.rstrip("\n")
            for marker in ("<<<FIM_SECAO>>>", "---"):
                if text.endswith(marker):
                    return text[: -len(marker)].rstrip("\n")
            return text

        section_found = False
        patched_parts = []

        for part in parts:
            stripped = part.strip()
            if not stripped or stripped in _DELIMITER_TOKENS:
                # Parte vazia ou é o próprio token de delimitador (preservado
                # exatamente como veio do split — nunca substituído).
                patched_parts.append(part)
                continue

            first_line = stripped.split("\n")[0].strip()
            matched_by_number = bool(section_id.isdigit() and re.match(rf'^{re.escape(section_id)}[.\s]', first_line))
            matched_by_heading = (first_line == section_id.strip())

            if not section_found and (matched_by_number or matched_by_heading):
                patched_parts.append(_strip_trailing_delimiter(new_content) + "\n")
                section_found = True
            else:
                patched_parts.append(part)

        if not section_found:
            return {
                "status": "warning",
                "section_found": False,
                "error": f"Seção '{section_id}' não encontrada em '{filename}'. Arquivo não alterado.",
                "hint": "Use read_analysis_sections para inspecionar os IDs disponíveis.",
            }

        destination.write_text("".join(patched_parts), encoding="utf-8")
        timestamp = datetime.now().isoformat()

        IOLogger.save(filename, caller=caller, backup=str(backup_path))

        return {
            "status": "ok",
            "path": str(destination),
            "section_found": True,
            "backup": str(backup_path),
            "timestamp": timestamp,
        }

    except Exception as e:
        IOLogger.error("patch_section", str(e), caller=caller)
        return {"status": "error", "error": str(e), "filename": filename}


# ──────────────────────────────────────────────────────────────────────────────
# Lock de Escrita (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def acquire_lock(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Adquire o lock de escrita exclusivo de um arquivo para o especialista `caller`.

    Enquanto o lock estiver ativo, somente o detentor pode modificar o arquivo
    (save_artifact, append_artifact e patch_section são bloqueados para os demais).
    A aquisição é atômica: dois especialistas nunca obtêm o mesmo lock ao mesmo
    tempo. Leituras nunca são afetadas por locks.

    Chamar novamente para um lock que você já possui é seguro (idempotente).

    ⚠️  Ao terminar as modificações, libere o lock com release_lock.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
                  Exemplos: "analise_tecnica_HU-001.md"
                            "PROTOTYPE/login.html"
        caller:   OBRIGATÓRIO — nome do especialista que precisa escrever.
                  Exemplo: "mermaid_specialist".

    Returns:
        Sucesso:  {"status": "ok", "locked": true, "owner": "<caller>", "filepath": "<nome>"}
        Ocupado:  {"status": "blocked", "locked": true, "owner": "<outro>", "error": "<motivo>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        if not caller or caller.strip().lower() in ("", "unknown"):
            return {
                "status": "error",
                "error": "Identificação obrigatória: informe em `caller` o nome do especialista que precisa do lock.",
            }
        caller = caller.strip()

        dirs = _resolve_dirs()
        _, filename, error = _resolve_path_arg(filepath, dirs)
        if error:
            return {"status": "error", "error": error}
        if not filename:
            return {"status": "error", "error": "Nome de arquivo vazio."}

        LOCKS_DIR.mkdir(parents=True, exist_ok=True)
        lock_file = _lock_path(filename)
        payload = json.dumps(
            {"owner": caller, "filepath": filename, "acquired_at": datetime.now().isoformat()},
            ensure_ascii=False,
        )

        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            current = _read_lock(lock_file) or {}
            owner = current.get("owner", "desconhecido")
            if owner == caller:
                return {
                    "status": "ok",
                    "locked": True,
                    "owner": caller,
                    "filepath": filename,
                    "msg": "Você já possuía o lock deste arquivo.",
                }
            return {
                "status": "blocked",
                "locked": True,
                "owner": owner,
                "filepath": filename,
                "error": (
                    f"Lock negado: '{filename}' já está com lock de '{owner}'. "
                    "Aguarde a liberação via release_lock pelo detentor."
                ),
            }

        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)

        IOLogger.lock(filename, caller=caller)
        return {"status": "ok", "locked": True, "owner": caller, "filepath": filename}

    except Exception as e:
        IOLogger.error("acquire_lock", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def check_lock(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Verifica se um arquivo está com lock de escrita ativo e quem é o detentor.

    Operação apenas de consulta — não adquire nem libera o lock.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
        caller:   Nome do agente solicitante (usado apenas para rastreabilidade).

    Returns:
        Livre:    {"status": "ok", "locked": false, "filepath": "<nome>"}
        Ocupado:  {"status": "ok", "locked": true, "owner": "<detentor>",
                   "acquired_at": "<ISO 8601>", "filepath": "<nome>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        dirs = _resolve_dirs()
        _, filename, error = _resolve_path_arg(filepath, dirs)
        if error:
            return {"status": "error", "error": error}
        if not filename:
            return {"status": "error", "error": "Nome de arquivo vazio."}

        lock_info = _read_lock(_lock_path(filename))
        if lock_info is None:
            return {"status": "ok", "locked": False, "filepath": filename}
        return {
            "status": "ok",
            "locked": True,
            "owner": lock_info.get("owner", "desconhecido"),
            "acquired_at": lock_info.get("acquired_at", ""),
            "filepath": filename,
        }

    except Exception as e:
        IOLogger.error("check_lock", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


def release_lock(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Libera o lock de escrita de um arquivo. Somente o detentor pode liberar.

    Use sempre após concluir as modificações em um arquivo cujo lock você
    adquiriu com acquire_lock, para permitir que outros especialistas escrevam.

    Args:
        filepath: Nome do arquivo, com ou sem alias de pasta.
        caller:   OBRIGATÓRIO — nome do especialista que possui o lock.

    Returns:
        Sucesso:  {"status": "ok", "released": true, "filepath": "<nome>"}
        Já livre: {"status": "ok", "released": false, "filepath": "<nome>", "msg": "<aviso>"}
        Negado:   {"status": "blocked", "released": false, "owner": "<detentor>", "error": "<motivo>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        dirs = _resolve_dirs()
        _, filename, error = _resolve_path_arg(filepath, dirs)
        if error:
            return {"status": "error", "error": error}
        if not filename:
            return {"status": "error", "error": "Nome de arquivo vazio."}

        lock_file = _lock_path(filename)
        lock_info = _read_lock(lock_file)
        if lock_info is None:
            return {
                "status": "ok",
                "released": False,
                "filepath": filename,
                "msg": "Nenhum lock ativo — o arquivo já estava livre.",
            }

        owner = lock_info.get("owner", "desconhecido")
        if owner != (caller or "").strip():
            return {
                "status": "blocked",
                "released": False,
                "owner": owner,
                "filepath": filename,
                "error": (
                    f"Liberação negada: o lock de '{filename}' pertence a '{owner}'. "
                    "Somente o detentor pode liberá-lo."
                ),
            }

        lock_file.unlink(missing_ok=True)
        IOLogger.unlock(filename, caller=caller)
        return {"status": "ok", "released": True, "filepath": filename}

    except Exception as e:
        IOLogger.error("release_lock", str(e), caller=caller)
        return {"status": "error", "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Interfaces entre fases — handoff via Manifesto (tasks 2.4 / 2.6)
# ──────────────────────────────────────────────────────────────────────────────
#
# O design já EMITE seu próprio Manifesto de Fase
# (`src/agents/workflow_design_pipeline/manifest.py`) e agora também LÊ o de
# outras fases (ver `00d_PREPARACAO_MANIFESTO_REQUISITOS_TIME2_DESIGN.md` e
# `extracao_manifesto_requisitos.md`).
#
# Confirmado por inspeção direta do lado Requisitos
# (`src/agents/requirements/manifest.py::emit_requirements_manifest`, plugado
# como `after_agent_callback` de `workflow_requirements`): a fase
# "requirements" JÁ publica `workspace_output/requirements/manifest.json` ao
# final de cada execução. O caso "absent" deixou de ser garantido — segue
# sendo tratado como estado neutro (ex.: antes da primeira run de Requisitos
# numa sessão), não como erro.
#
# Ponto crítico confirmado (ver `extracao_manifesto_requisitos.md`, seção 5):
# os `path` gravados pelo emissor de Requisitos são relativos à RAIZ DO
# WORKSPACE (`get_workspace_root()`, que já É `workspace_output/`) — ex.:
# "requirements/HUs/HU-001.md", SEM o prefixo "workspace_output/". Isso é
# diferente da convenção que o próprio manifesto de Design usa para os SEUS
# artifacts (`workflow_design_pipeline/manifest.py::_repo_relative`, relativo
# à raiz do repo, COM o prefixo "workspace_output/"). `read_phase_artifact`
# resolve pela convenção confirmada (sem prefixo) e normaliza defensivamente
# um prefixo "workspace_output/" caso apareça — ver docstring da função.

def read_phase_manifest(
    phase: str,
    tipo: str | None = None,
    caller: str | None = "unknown",
) -> Dict[str, Any]:
    """
    Lê o Manifesto de Fase (`manifest.json`) publicado por OUTRA fase do SDLC
    (ex.: "requirements"), para ler `artifacts[].path` em vez de depender de
    texto acumulado (ver `time2_design_tasks.md`, tasks 2.4 e 2.6).

    ⚠️  Diferente das demais funções deste módulo, esta NÃO aceita `base_dir`
    de workspace isolado do design — ela lê deliberadamente a raiz do
    workspace inteiro (`get_workspace_root()`), porque o manifesto que
    interessa aqui é o de OUTRA fase, não o do próprio design.

    A ausência do manifesto é tratada como estado neutro (a fase de origem
    ainda não rodou nesta sessão) — trate "absent" como "prossiga com o fluxo
    atual", nunca como falha ou motivo de bloqueio do design.

    Args:
        phase:  Nome canônico da fase de origem (ex.: "requirements"),
                correspondente à subpasta em workspace_output/.
        tipo:   Filtro determinístico opcional sobre `manifest["artifacts"]`
                (ex.: "HU"). Quando informado, a lista `artifacts` retornada
                contém só os itens com esse `tipo` exato — `doubts`,
                `status` e `summary` são sempre repassados integralmente,
                sem filtro (dúvidas não bloqueantes de outros tipos de
                artefato continuam relevantes para o chamador). Existe para
                que o filtro por tipo (ex.: só HUs para o design_architect,
                nunca RFs/RNFs/RNs/Glossário) seja aplicado de forma
                determinística aqui, e não deixado a critério de leitura do
                LLM chamador — ver `extracao_manifesto_requisitos.md`,
                seção 6. Sem filtro (`tipo=None`), o comportamento é idêntico
                ao anterior: `artifacts` vem cru, sem nenhuma interpretação
                de campo feita pelo design.
        caller: Nome do agente solicitante (rastreabilidade).

    Returns:
        Ausente: {"status": "absent", "phase": "<phase>",
                   "hint": "Fase '<phase>' ainda não publicou manifest.json — use o fluxo atual (texto colado)."}
        Sucesso: {"status": "ok", "phase": "<phase>", "manifest": {<JSON, com "artifacts" filtrado por tipo, se pedido>}}
        Falha:   {"status": "error", "phase": "<phase>", "error": "<motivo>"}
    """
    import json
    from shared.workspace import get_workspace_root

    _MANIFEST_FILENAME = "manifest.json"

    try:
        manifest_path = (get_workspace_root() / phase / _MANIFEST_FILENAME).resolve()

        if not manifest_path.exists():
            IOLogger.read(f"{phase}/{_MANIFEST_FILENAME} [absent]", caller=caller)
            return {
                "status": "absent",
                "phase": phase,
                "hint": (
                    f"Fase '{phase}' ainda não publicou {_MANIFEST_FILENAME} — "
                    "use o fluxo atual (texto colado) até que ela passe a emitir."
                ),
            }

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        if not isinstance(manifest, dict) or "artifacts" not in manifest:
            return {
                "status": "error",
                "phase": phase,
                "error": f"{_MANIFEST_FILENAME} encontrado mas fora do formato esperado (faltando 'artifacts').",
            }

        if tipo is not None:
            manifest = {
                **manifest,
                "artifacts": [
                    a for a in manifest.get("artifacts", [])
                    if isinstance(a, dict) and a.get("tipo") == tipo
                ],
            }

        IOLogger.read(f"{phase}/{_MANIFEST_FILENAME}", caller=caller)
        return {"status": "ok", "phase": phase, "manifest": manifest}

    except (OSError, ValueError) as e:
        IOLogger.error("read_phase_manifest", str(e), caller=caller)
        return {"status": "error", "phase": phase, "error": str(e)}


def read_phase_artifact(path: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê o conteúdo de um artefato referenciado pelo campo `path` de um
    ManifestArtifact de OUTRA fase (ver read_phase_manifest acima).

    Diferente de read_file/read_multiple_files (que só enxergam as pastas do
    próprio design via alias), esta função resolve `path` relativo à RAIZ DO
    WORKSPACE (`get_workspace_root()`, que já É `workspace_output/`) — a
    convenção confirmada por inspeção direta do emissor real de Requisitos
    (`src/agents/requirements/manifest.py::_scan_artifacts`, que grava
    `path` via `f.relative_to(ws_root)`). Um `path` real hoje se parece com
    "requirements/HUs/HU-001.md" — SEM o prefixo "workspace_output/".

    Isso é diferente da convenção que o próprio manifesto de Design usa
    (`workflow_design_pipeline/manifest.py::_repo_relative`, relativo à raiz
    do repo, COM o prefixo "workspace_output/"). Como essa divergência entre
    fases é uma possibilidade real (cada emissor decide sua própria
    convenção hoje), esta função resolve primeiro pela convenção confirmada
    (sem prefixo) e, defensivamente, tenta de novo removendo um eventual
    prefixo "workspace_output/" antes de desistir — nunca aceita o path como
    absoluto nem sai de dentro de workspace_output/, porque `path` vem de um
    manifesto de OUTRA fase (dado externo ao design, não confiável por
    padrão).

    Args:
        path:   Caminho relativo, exatamente como aparece em
                manifest["artifacts"][i]["path"].
        caller: Nome do agente solicitante (rastreabilidade).

    Returns:
        Sucesso: {"status": "ok", "path": "<path>", "content": "<conteúdo>"}
        Falha:   {"status": "error", "path": "<path>", "error": "<motivo>"}
    """
    from shared.workspace import get_workspace_root

    try:
        workspace_root = get_workspace_root().resolve()

        # Convenção confirmada (extracao_manifesto_requisitos.md, seção 5):
        # path já é relativo a workspace_root, sem prefixo.
        candidate = (workspace_root / path).resolve()

        # Normalização defensiva: se o path real vier com o prefixo que o
        # manifesto de Design usa para si mesmo ("workspace_output/..."),
        # aceita também — sem isso, um manifesto de outra fase que adote essa
        # convenção seria recusado por engano.
        if not candidate.exists():
            prefix = f"{workspace_root.name}/"
            if path.startswith(prefix):
                candidate = (workspace_root / path[len(prefix):]).resolve()

        if not candidate.is_relative_to(workspace_root):
            return {
                "status": "error",
                "path": path,
                "error": "Acesso negado: caminho fora de workspace_output/.",
            }

        if not candidate.exists():
            return {"status": "error", "path": path, "error": f"Artefato '{path}' não encontrado."}

        content = candidate.read_text(encoding="utf-8")
        IOLogger.read(path, caller=caller)
        return {"status": "ok", "path": path, "content": content}

    except (OSError, ValueError) as e:
        IOLogger.error("read_phase_artifact", str(e), caller=caller)
        return {"status": "error", "path": path, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Mocks
# ──────────────────────────────────────────────────────────────────────────────

def list_versions(filepath: str) -> dict:
    """Mock: lista versões anteriores de um artefato."""
    return {"status": "ok", "versions": [], "filepath": filepath}
