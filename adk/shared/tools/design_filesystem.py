"""
design_filesystem.py
─────────────
Camada de persistência usada exclusivamente pelo Agente IO.
Responsabilidade: ler, salvar, promover e listar artefatos em disco.

Logging de operações delegado integralmente ao IOLogger (design_logger.py).
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .design_logger import IOLogger

def _find_root(start_path: Path, target: str = "adk") -> Path:
    for parent in start_path.parents:
        if parent.name == target:
            return parent
    return start_path.parents[4]  # Fallback seguro (Atualizar se necessário)

CURRENT_DIR = _find_root(Path(__file__).resolve())
STAGING_DIR = CURRENT_DIR / "temp" / "staging"
OFFICIAL_DIR = CURRENT_DIR / "artifacts"
PROTOTYPE_DIR = STAGING_DIR / "prototype"
LOG_FILENAME = "io_operations.log"
STATUS_IN_REVIEW = "**Status:** Em análise"
STATUS_BLOCKED = "**Status:** Bloqueado"
BACKUP_PREFIX = "_backup_"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers Privados
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)
    PROTOTYPE_DIR.mkdir(parents=True, exist_ok=True)


def _is_safe_path(path: Path) -> bool:
    try:
        resolved_path = path.resolve()
        return resolved_path.is_relative_to(CURRENT_DIR.resolve())
    except (ValueError, RuntimeError):
        return False


def _next_version(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.parent / f"{path.stem}{BACKUP_PREFIX}{timestamp}{path.suffix}"

# ──────────────────────────────────────────────────────────────────────────────
# Funções Públicas (Ferramentas do Agente)
# ──────────────────────────────────────────────────────────────────────────────

def read_file(filepath: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê e retorna o conteúdo completo de um arquivo em staging ou no sistema de arquivos do projeto.
 
    Use quando precisar do conteúdo de um arquivo específico cujo caminho você já conhece —
    por exemplo, ler um Doubt_Artifact para verificar se foi resolvido, ou ler um HTML
    já salvo para validação.
 
    Para ler vários arquivos de uma vez, prefira read_multiple_files.
    Para ler só algumas seções de uma analise_tecnica_, prefira read_analysis_sections.
 
    Args:
        filepath: Caminho do arquivo. Pode ser absoluto ou relativo ao projeto.
                  Exemplos: "temp/staging/relatorio_HU-001.md"
                            "temp/staging/prototype/login.html"
        caller:   Nome do agente que está fazendo a leitura (ex: "prototyping_specialist").
                  Usado apenas para rastreabilidade no log — não afeta o resultado.
 
    Returns:
        Sucesso:  {"status": "ok",    "content": "<conteúdo do arquivo>"}
        Falha:    {"status": "error", "error":   "<motivo>"}
    """
    try:
        path = Path(filepath).resolve()

        if not path.exists():
            if filepath.endswith(".html") or filepath.endswith(".css"):
                alt_path = (PROTOTYPE_DIR / Path(filepath).name).resolve()
                if alt_path.exists():
                    path = alt_path

        if not _is_safe_path(path):
            return {"status": "error", "error": "Acesso negado: o caminho solicitado está fora do diretório do projeto."}

        if not path.exists():
            return {"status": "error", "error": f"Arquivo {filepath} não encontrado."}

        content = path.read_text(encoding="utf-8")
        IOLogger.read(path.name, caller=caller)
        return {"status": "ok", "content": content}

    except Exception as e:
        IOLogger.error("read_file", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def read_analysis_sections(filepath: str, sections: list[int], caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê seções específicas de um arquivo analise_tecnica_.md, ignorando o restante.
 
    Use quando precisar de apenas uma parte da análise técnica — por exemplo, só
    a seção 8 (Plano de Prototipação) ou as seções 4 e 8 (Componentes + Plano).
    Isso reduz o volume de texto retornado e evita carregar o arquivo inteiro.
 
    O arquivo deve seguir o formato padrão do design_architect: cada seção começa
    com "<número>. <Título>" e termina com "---".
    Se as seções solicitadas não forem encontradas, retorna o arquivo completo com aviso.
 
    Args:
        filepath: Caminho do arquivo analise_tecnica_ em staging.
                  Exemplo: "temp/staging/analise_tecnica_HU-001_HU-002.md"
        sections: Lista de números inteiros das seções desejadas.
                  Exemplo: [4, 8] retorna apenas as seções 4 e 8.
                  Exemplo: [1, 3, 4] retorna as seções 1, 3 e 4.
        caller:   Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        Sucesso:  {"status": "ok",      "content": "<seções solicitadas concatenadas>"}
        Aviso:    {"status": "warning", "content": "<arquivo completo>",
                   "msg": "Não foi possível extrair as seções. Retornando arquivo completo."}
        Falha:    {"status": "error",   "error":   "<motivo>"}
    """
    try:
        import re
        path = Path(filepath).resolve()

        if not path.exists():
            if filepath.endswith(".html") or filepath.endswith(".css"):
                alt_path = (PROTOTYPE_DIR / Path(filepath).name).resolve()
                if alt_path.exists():
                    path = alt_path

        if not _is_safe_path(path):
            return {"status": "error", "error": "Acesso negado: o caminho solicitado está fora do diretório do projeto."}

        if not path.exists():
            return {"status": "error", "error": f"Arquivo {filepath} não encontrado."}

        content = path.read_text(encoding="utf-8")
        
        # O arquivo de análise usa '---' para separar seções primárias
        parts = re.split(r'\n---\n', content)
        
        extracted = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            first_line = part.split('\n')[0].strip()
            match = re.match(r'^(\d+)\.', first_line)
            
            if match:
                sec_num = int(match.group(1))
                if sec_num in sections:
                    extracted.append(part)
                
        IOLogger.read(path.name + f" [sections:{sections}]", caller=caller)

        if not extracted:
            return {"status": "warning", "content": content, "msg": "Não foi possível extrair as seções solicitadas. Retornando arquivo completo."}
            
        return {"status": "ok", "content": "\n\n---\n\n".join(extracted)}

    except Exception as e:
        IOLogger.error("read_analysis_sections", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def read_multiple_files(filepaths: list[str], caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lê o conteúdo de vários arquivos em uma única chamada e os retorna juntos.
 
    Use quando precisar validar ou processar um conjunto de arquivos de uma vez —
    por exemplo, auditar todos os HTMLs e o global.css após geração do protótipo,
    ou ler todos os diagramas .mmd de um lote para validação.
    Mais eficiente do que chamar read_file repetidamente.
 
    Arquivos não encontrados ou inacessíveis são retornados individualmente com erro,
    sem impedir a leitura dos demais.
 
    Args:
        filepaths: Lista de caminhos dos arquivos a serem lidos.
                   Exemplo: ["temp/staging/prototype/login.html",
                             "temp/staging/prototype/global.css"]
        caller:    Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        Sucesso:  {"status": "ok", "contents": {
                      "<filepath>": {"status": "ok",    "content": "<conteúdo>"},
                      "<filepath>": {"status": "error", "error":   "<motivo>"},
                      ...
                  }}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        contents = {}
        for filepath in filepaths:
            path = Path(filepath).resolve()

            if not path.exists():
                if filepath.endswith(".html") or filepath.endswith(".css"):
                    alt_path = (PROTOTYPE_DIR / Path(filepath).name).resolve()
                    if alt_path.exists():
                        path = alt_path

            if not _is_safe_path(path):
                contents[filepath] = {"status": "error", "error": "Acesso negado fora do diretório."}
                continue

            if not path.exists():
                contents[filepath] = {"status": "error", "error": "Arquivo não encontrado."}
                continue    

            content = path.read_text(encoding="utf-8")
            contents[filepath] = {"status": "ok", "content": content}

        # Identifica tipos de arquivos únicos para o log
        file_types = {Path(f).suffix.lstrip('.').lower() for f in filepaths if '.' in f}
        str_file_types = ", ".join(file_types) if file_types else "sem extensão"
            
        IOLogger.read(f"[batch: {len(filepaths)} files | types: {str_file_types}]", caller=caller)
        return {"status": "ok", "contents": contents}

    except Exception as e:
        IOLogger.error("read_multiple_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def save_artifact(filename: str, content: str, caller: str | None = "unknown") -> dict:
    """
    Salva um arquivo em staging. Se o arquivo já existir, cria backup automático antes de sobrescrever.
 
    Use para criar um arquivo novo ou substituir completamente um existente.
    Arquivos .html e global.css são salvos automaticamente em staging/prototype/.
    Todos os outros arquivos são salvos em staging/.
 
    ⚠️  Esta função SOBRESCREVE o arquivo inteiro. Para adicionar conteúdo ao fim
        de um arquivo existente sem apagar o que já está lá, use append_artifact.
    ⚠️  Para corrigir apenas uma seção de um arquivo Markdown, use patch_section.
 
    Args:
        filename: Nome do arquivo a ser salvo. Não inclua caminhos como "staging/" ou "prototype/" —
                  o sistema resolve o destino automaticamente pelo tipo de arquivo.
                  Exemplos: "analise_tecnica_HU-001_HU-002.md"
                            "relatorio_HU-001.md"
                            "diagrama_HU-001_login.mmd"
                            "login.html"          → salvo em staging/prototype/
                            "global.css"          → salvo em staging/prototype/
                            "prototype/login.html"→ equivalente a "login.html"
        content:  Conteúdo completo do arquivo como string.
        caller:   Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        Sucesso:  {"status": "ok", "path": "<caminho completo>",
                   "versioned_backup": "<caminho do backup ou vazio se não havia arquivo>",
                   "timestamp": "<ISO 8601>"}
        Falha:    {"status": "error", "error": "<motivo>", "filename": "<nome>"}
    """
    try:
        _ensure_dirs()

        clean_filename = filename.replace("prototype/", "").replace("staging/", "")

        target_dir = STAGING_DIR
        if clean_filename.endswith(".html") or clean_filename == "global.css":
            target_dir = PROTOTYPE_DIR

        destination = (target_dir / clean_filename).resolve()

        if not _is_safe_path(destination):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        destination.parent.mkdir(parents=True, exist_ok=True)

        versioned_backup = None
        if destination.exists():
            backup_path = _next_version(destination)
            shutil.move(str(destination), str(backup_path))
            versioned_backup = str(backup_path)

        destination.write_text(content, encoding="utf-8")
        timestamp = datetime.now().isoformat()
        if not versioned_backup:
            versioned_backup = ""

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

def promote_artifact(filename: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Copia um relatório aprovado de staging para artifacts/ (diretório oficial permanente).
 
    Use somente quando o solicitante tiver alterado o status do relatório para "Aprovado"
    e pedir explicitamente a promoção. Nunca promova sem verificar o status antes.
 
    Restrições aplicadas automaticamente pela função:
    - Apenas arquivos .md cujo nome contenha "relatorio" podem ser promovidos.
    - O arquivo deve conter "**Status:** Aprovado" — se ainda contiver "**Status:** Em análise",
      a promoção é bloqueada e retorna status "blocked".
    - Diagramas .mmd, HTMLs, CSS e a analise_tecnica_ nunca são promovidos — permanecem em staging.
 
    Args:
        filename: Nome exato do relatório em staging.
                  Exemplo: "relatorio_HU-001_HU-002_HU-003.md"
        caller:   Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        Sucesso:  {"status": "ok",      "source": "<origem>", "destination": "<destino>",
                   "timestamp": "<ISO 8601>"}
        Bloqueio: {"status": "blocked", "reason": "<motivo>", "file": "<nome>"}
        Falha:    {"status": "error",   "error":  "<motivo>"}
    """
    try:
        raw_filename = Path(filename)
        if raw_filename.is_absolute() or ".." in raw_filename.parts:
            raise PermissionError("Segurança: Caminho inválido.")

        source = (STAGING_DIR / raw_filename).resolve()
        if not _is_safe_path(source):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        if not source.exists():
            return {"status": "error", "error": f"Arquivo {filename} não encontrado em staging."}

        if source.suffix != ".md":
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos para artifacts. Diagramas .mmd permanecem em staging.",
                "file": filename,
            }

        if "relatorio" not in filename:
            return {
                "status": "blocked",
                "reason": "Apenas relatórios .md podem ser promovidos para artifacts. A analise tecnica permanece em staging.",
                "file": filename,
            }

        content = source.read_text(encoding="utf-8")
        if STATUS_IN_REVIEW in content:
            return {
                "status": "blocked",
                "reason": f"O relatório ainda possui o marcador '{STATUS_IN_REVIEW}'. Aprovação manual necessária.",
                "file": filename,
            }

        _ensure_dirs()
        destination = (OFFICIAL_DIR / raw_filename).resolve()
        if not _is_safe_path(destination):
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

def list_staging_files(filetype: str = "", caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Lista os arquivos presentes em staging (e em staging/prototype/ para .html e .css).
 
    Use como primeira ação ao iniciar qualquer agente, para descobrir o que já existe
    em staging antes de gerar ou sobrescrever qualquer coisa. Também útil para verificar
    se um arquivo específico foi salvo com sucesso.
 
    Backups (nomes com "_backup_") e o arquivo de log são excluídos automaticamente da listagem.
 
    Args:
        filetype: Extensão para filtrar a listagem, sem o ponto.
                  Exemplos: "md"  → lista apenas arquivos .md
                            "mmd" → lista apenas arquivos .mmd
                            "html"→ lista apenas arquivos .html em staging/prototype/
                            ""    → lista todos os arquivos (padrão)
        caller:   Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        Sucesso:  {"status": "ok", "files": ["arquivo1.md", "arquivo2.mmd", ...],
                   "staging_dir": "<caminho absoluto do staging>"}
        Falha:    {"status": "error", "error": "<motivo>"}
    """
    try:
        _ensure_dirs()

        files = [
            f.name
            for f in sorted(STAGING_DIR.iterdir())
            if f.is_file()
            and f.name != LOG_FILENAME
            and BACKUP_PREFIX not in f.name
            and (not filetype or f.suffix == f".{filetype}")
        ]

        if not filetype or filetype in ["html", "css"]:
            proto_files = [
                f.name
                for f in sorted(PROTOTYPE_DIR.iterdir())
                if f.is_file()
                and BACKUP_PREFIX not in f.name
                and (not filetype or f.suffix == f".{filetype}")
            ]
            files.extend(proto_files)

        IOLogger.read(f"[list:{filetype or 'all'}]", caller=caller)
        return {"status": "ok", "files": sorted(list(set(files))), "staging_dir": str(STAGING_DIR)}

    except Exception as e:
        IOLogger.error("list_staging_files", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def check_active_blocks(caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Verifica se há Doubt_Artifacts com status "Bloqueado" em staging.
 
    Use após receber retomada de um bloqueio, para confirmar que todos os
    Doubt_Artifacts foram realmente resolvidos antes de prosseguir o pipeline.
    Também usado pelo pipeline_controller como gate antes de emitir PIPELINE_STAGE_1_COMPLETE.
 
    Um Doubt_Artifact é considerado bloqueado se seu conteúdo contiver a linha:
    "**Status:** Bloqueado"
    Após resolução, o solicitante deve alterar essa linha para "**Status:** Resolvido"
    para que este check retorne has_blocks: false.
 
    Args:
        caller: Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        Sucesso sem bloqueios: {"status": "ok", "has_blocks": false, "blocks": []}
        Sucesso com bloqueios: {"status": "ok", "has_blocks": true,
                                "blocks": [{"filename": "<nome>", "hu_id": "<HU_ID>"}, ...]}
        Falha:                 {"status": "error", "error": "<motivo>"}
    """
    try:
        _ensure_dirs()
        blocks = []
        for f in sorted(STAGING_DIR.iterdir()):
            if f.name.startswith("Doubt_Artifact_") and BACKUP_PREFIX not in f.name:
                content = f.read_text(encoding="utf-8")
                if STATUS_BLOCKED in content:
                    parts = f.stem.split("_")
                    hu_id = parts[2] if len(parts) >= 3 else "desconhecido"
                    blocks.append({"filename": f.name, "hu_id": hu_id})

        IOLogger.read("[check_active_blocks]", caller=caller)
        return {"status": "ok", "has_blocks": len(blocks) > 0, "blocks": blocks}

    except Exception as e:
        IOLogger.error("check_active_blocks", str(e), caller=caller)
        return {"status": "error", "error": str(e)}

def clear_staging_folder(caller: str | None = "unknown") -> bool:
    """
    Remove todos os arquivos de staging e seus subdiretórios (incluindo staging/prototype/).
    A estrutura de pastas é preservada — apenas os arquivos são deletados.
 
    Use exclusivamente no início de um novo ciclo do pipeline, para garantir que
    artefatos de execuções anteriores não contaminem o lote atual.
    Esta operação é irreversível — não há backup dos arquivos removidos.
 
    ⚠️  Nunca chame esta função no meio de uma execução ativa do pipeline.
 
    Args:
        caller: Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        True  → todos os arquivos foram removidos com sucesso.
        False → ocorreu um erro durante a limpeza (detalhes no log de operações).
    """
    try:
        _ensure_dirs()

        def _clear_recursive(directory: Path):
            if not _is_safe_path(directory):
                return
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    _clear_recursive(item)

        _clear_recursive(STAGING_DIR)
        IOLogger.erase(str(STAGING_DIR), caller=caller)
        return True
    except Exception as e:
        IOLogger.error("ERASE", f"dir={STAGING_DIR} | error={str(e)}", caller=caller)
        return False

def append_artifact(filename: str, content: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Adiciona conteúdo ao fim de um arquivo existente em staging, sem apagar o que já está lá.
    Se o arquivo não existir, cria-o (comportamento idêntico ao save_artifact).
 
    Use para construir arquivos longos de forma incremental — por exemplo, adicionar
    seções a um relatório ou à analise_tecnica_ uma a uma, sem precisar reescrever
    o arquivo inteiro a cada vez.
 
    ⚠️  Diferente de save_artifact, esta função NÃO cria backup. O conteúdo é apenas
        acrescentado ao fim. Para substituir o arquivo inteiro, use save_artifact.
    ⚠️  Para corrigir apenas uma seção já escrita, use patch_section.
 
    Args:
        filename: Nome do arquivo em staging. O sistema resolve o destino automaticamente:
                  .html e global.css → staging/prototype/
                  demais             → staging/
                  Exemplo: "analise_tecnica_HU-001.md"
                           "relatorio_HU-001.md"
                           "global.css"
        content:  Trecho a ser adicionado ao fim do arquivo.
                  Inclua o separador "---" ao final se for uma seção de analise_tecnica_.
        caller:   Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
    Returns:
        Sucesso:  {"status": "ok", "path": "<caminho>",
                   "bytes_total": <tamanho total do arquivo após append>,
                   "timestamp": "<ISO 8601>"}
        Falha:    {"status": "error", "error": "<motivo>", "filename": "<nome>"}
    """
    try:
        _ensure_dirs()

        clean_filename = filename.replace("prototype/", "").replace("staging/", "")
        target_dir = STAGING_DIR
        if clean_filename.endswith(".html") or clean_filename == "global.css":
            target_dir = PROTOTYPE_DIR

        destination = (target_dir / clean_filename).resolve()

        if not _is_safe_path(destination):
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

def patch_section(filename: str, section_id: str, new_content: str, caller: str | None = "unknown") -> Dict[str, Any]:
    """
    Substitui uma seção específica de um arquivo Markdown em staging, sem alterar as demais.
 
    Use quando precisar corrigir o conteúdo de uma seção já escrita — por exemplo,
    atualizar a seção 5 (Bloqueios) após resolução de um Doubt_Artifact, ou corrigir
    a seção 8 (Plano de Prototipação) sem reescrever o arquivo inteiro.
 
    A seção é identificada de duas formas (o primeiro match encontrado vence):
    - Por número: section_id="4" encontra a seção cuja primeira linha começa com "4." ou "4 ".
    - Por heading Markdown exato: section_id="## Título" encontra a seção com esse heading.
 
    ⚠️  section_id deve ser APENAS o número isolado ("4", "5", "8") ou o heading exato.
        Nunca passe o título junto com o número ("4. Identificação...") — não será encontrado.
    ⚠️  new_content deve incluir o título da seção na primeira linha e terminar com "---".
        Exemplo: "4. Identificação de Componentes por HU\n<conteúdo>\n---\n"
    ⚠️  Para seções escritas em múltiplos appends (ex: seção 4 em lotes grandes),
        new_content deve conter o conteúdo completo e consolidado da seção inteira.
    ⚠️  Um backup automático é criado antes de qualquer alteração.
 
    Args:
        filename:    Nome do arquivo em staging.
                     Exemplo: "analise_tecnica_HU-001_HU-002.md"
        section_id:  Número isolado ("4") ou heading Markdown exato ("## Título").
        new_content: Conteúdo completo da seção corrigida, incluindo título e "---" final.
        caller:      Nome do agente solicitante. Usado apenas para rastreabilidade no log.
 
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

        _ensure_dirs()

        clean_filename = filename.replace("prototype/", "").replace("staging/", "")
        target_dir = STAGING_DIR
        if clean_filename.endswith(".html") or clean_filename == "global.css":
            target_dir = PROTOTYPE_DIR

        destination = (target_dir / clean_filename).resolve()

        if not _is_safe_path(destination):
            raise PermissionError("Segurança: Tentativa de escrita fora da área permitida.")

        if not destination.exists():
            return {"status": "error", "error": f"Arquivo {filename} não encontrado em staging. Use save_artifact para criar."}

        original = destination.read_text(encoding="utf-8")

        # Backup automático antes de qualquer patch
        backup_path = _next_version(destination)
        shutil.copy2(str(destination), str(backup_path))

        # Divide por separador '---' (padrão do design_architect)
        separator = "\n---\n"
        parts = re.split(r'(?<=\n)---\n', original)

        section_found = False
        patched_parts = []

        for part in parts:
            stripped = part.strip()
            if not stripped:
                patched_parts.append(part)
                continue

            first_line = stripped.split("\n")[0].strip()

            # Match por número: "3." ou "3 —" no início
            matched_by_number = bool(section_id.isdigit() and re.match(rf'^{re.escape(section_id)}[.\s]', first_line))
            # Match por heading Markdown: "## Título"
            matched_by_heading = (first_line == section_id.strip())

            if not section_found and (matched_by_number or matched_by_heading):
                # Preserva a quebra de linha final do separador se existia
                patched_parts.append(new_content.rstrip("\n") + "\n")
                section_found = True
            else:
                patched_parts.append(part)

        if not section_found:
            # Seção não encontrada: não altera o arquivo, retorna aviso
            return {
                "status": "warning",
                "section_found": False,
                "error": f"Seção '{section_id}' não encontrada em {filename}. Arquivo não alterado.",
                "hint": "Use read_analysis_sections para inspecionar os IDs disponíveis.",
            }

        new_text = "---\n".join(patched_parts)
        destination.write_text(new_text, encoding="utf-8")
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
# Mocks
# ──────────────────────────────────────────────────────────────────────────────

def check_lock(filepath: str) -> dict:
    """Mock: verifica se o arquivo está bloqueado por outro agente."""
    return {"status": "ok", "locked": False, "filepath": filepath}


def release_lock(filepath: str) -> dict:
    """Mock: libera o lock do arquivo após escrita."""
    return {"status": "ok", "released": True, "filepath": filepath}


def list_versions(filepath: str) -> dict:
    """Mock: lista versões anteriores de um artefato."""
    return {"status": "ok", "versions": [], "filepath": filepath}