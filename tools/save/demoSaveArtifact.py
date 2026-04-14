"""
demo_save_artifact.py
─────────────────────
Script de demonstração — Definição de Pronto (DoD)
 
Prova que:
  ✅ Agente consegue salvar em pasta permitida
  ❌ Agente é bloqueado ao tentar salvar em pasta proibida
  ✅ Versionamento automático funciona
  ✅ Staging → promoção com aprovação funciona
  ❌ Promoção sem aprovação é bloqueada
 
Execute:
    python demo_save_artifact.py
"""
 
import json
import os
import sys
import tempfile
from pathlib import Path
 
# ── Aponta REPO_ROOT para um diretório temporário (auto-contido) ──────────────
_TEMP_ROOT = tempfile.mkdtemp(prefix="repo_demo_")
os.environ["REPO_ROOT"] = _TEMP_ROOT
 
# Importa APÓS definir REPO_ROOT (o módulo lê a env var no import)
from tools.save.saveDiagram import (
    save_artifact,
    promote_artifact,
    check_lock,
    release_lock,
    list_versions,
    ALLOWED_DIRS,
    _REPO_ROOT,
)
 
# ─────────────────────────────────────────────────────────────────────────────
# Helpers de exibição
# ─────────────────────────────────────────────────────────────────────────────
 
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
 
def _header(title: str):
    print(f"\n{BOLD}{CYAN}{'═'*64}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*64}{RESET}")
 
def _result(result: dict, expect_success: bool):
    ok   = result.get("success", False)
    icon = f"{GREEN}✅ PASSOU{RESET}" if ok == expect_success else f"{RED}❌ FALHOU{RESET}"
    label = "PERMITIDO" if expect_success else "BLOQUEADO (esperado)"
    print(f"  {icon}  [{label}]")
    print(f"  {YELLOW}→{RESET} {result.get('message', '')}")
    if result.get("staging_path"):
        print(f"  {YELLOW}→{RESET} staging_path: {result['staging_path']}")
    if result.get("final_path"):
        print(f"  {YELLOW}→{RESET} final_path:   {result['final_path']}")
    if result.get("versions"):
        print(f"  {YELLOW}→{RESET} versões:      {result['versions']}")
    return ok == expect_success
 
pass_count = 0
fail_count = 0
 
def _check(result: dict, expect_success: bool, label: str):
    global pass_count, fail_count
    ok = _result(result, expect_success)
    if ok:
        pass_count += 1
    else:
        fail_count += 1
        print(f"  {RED}  ↳ Detalhe completo: {json.dumps(result, ensure_ascii=False)}{RESET}")
 
# ─────────────────────────────────────────────────────────────────────────────
# Conteúdo de exemplo
# ─────────────────────────────────────────────────────────────────────────────
 
PUML_CONTENT = """\
@startuml
class User {
  +id: UUID
  +name: String
  +email: String
}
class Order {
  +id: UUID
  +total: Decimal
}
User "1" --> "N" Order : places
@enduml
"""
 
MMD_CONTENT = """\
flowchart TD
    A[Supervisor] --> B[Arquiteto]
    B --> C[Parser/Validator]
    C -->|válido| D[Save Artifact Tool]
    C -->|inválido| B
    D --> E[Staging]
    E -->|aprovado| F[Repositório Git]
"""
 
MD_CONTENT = """\
# Decisão de Arquitetura: Sistema Multi-Agente A2A
 
## Contexto
Necessidade de orquestrar múltiplos agentes LLM com controle de persistência.
 
## Decisão
Adotar padrão de Gatekeeper determinístico antes de qualquer escrita.
 
## Consequências
- Artefatos inválidos nunca chegam ao repositório.
- Humano mantém controle via área de staging.
"""
 
# ═════════════════════════════════════════════════════════════════════════════
# BLOCO 1 — Caminhos PROIBIDOS (devem ser bloqueados)
# ═════════════════════════════════════════════════════════════════════════════
 
_header("BLOCO 1 — Tentativas em diretórios PROIBIDOS (todas devem ser bloqueadas)")
 
print(f"\n  Repo root de teste: {_REPO_ROOT}\n")
 
_check(
    save_artifact(PUML_CONTENT, "secret.puml", relative_path=".env/secret.puml"),
    expect_success=False,
    label="Escrita em .env/",
)
_check(
    save_artifact(PUML_CONTENT, "arch.puml", relative_path="src/arch.puml"),
    expect_success=False,
    label="Escrita em /src",
)
_check(
    save_artifact(PUML_CONTENT, "arch.puml", relative_path="app/models/arch.puml"),
    expect_success=False,
    label="Escrita em /app",
)
_check(
    save_artifact(PUML_CONTENT, "arch.puml", relative_path="../../etc/passwd"),
    expect_success=False,
    label="Path traversal ../../",
)
_check(
    save_artifact(PUML_CONTENT, "arch.puml", relative_path="config/settings.puml"),
    expect_success=False,
    label="Escrita em /config",
)
_check(
    save_artifact("", "vazio.puml", relative_path="docs/Time_2_Design/diagrams/vazio.puml"),
    expect_success=False,
    label="Conteúdo vazio",
)
 
# ═════════════════════════════════════════════════════════════════════════════
# BLOCO 2 — Caminhos PERMITIDOS (devem funcionar)
# ═════════════════════════════════════════════════════════════════════════════
 
_header("BLOCO 2 — Salvamento em diretórios PERMITIDOS (todos devem passar)")
 
_check(
    save_artifact(PUML_CONTENT, "arch.puml", relative_path="docs/Time_2_Design/diagrams/arch.puml"),
    expect_success=True,
    label="PlantUML em docs/Time_2_Design/diagrams/",
)
_check(
    save_artifact(MMD_CONTENT, "flow.mmd", relative_path="docs/Time_2_Design/diagrams/flow.mmd"),
    expect_success=True,
    label="Mermaid em docs/Time_2_Design/diagrams/",
)
_check(
    save_artifact(MD_CONTENT, "adr-001.md", relative_path="docs/Time_2_Design/architecture/adr-001.md"),
    expect_success=True,
    label="Markdown em docs/Time_2_Design/architecture/",
)
 
# ── Mapeamento automático por extensão (sem relative_path)
_check(
    save_artifact(PUML_CONTENT, "auto_arch.puml"),
    expect_success=True,
    label="Auto-mapeamento .puml → docs/Time_2_Design/diagrams/",
)
_check(
    save_artifact(MD_CONTENT, "auto_doc.md"),
    expect_success=True,
    label="Auto-mapeamento .md → docs/Time_2_Design/architecture/",
)
 
# ═════════════════════════════════════════════════════════════════════════════
# BLOCO 3 — Versionamento automático
# ═════════════════════════════════════════════════════════════════════════════
 
_header("BLOCO 3 — Versionamento automático (segunda escrita cria _v2)")
 
PUML_V2 = PUML_CONTENT.replace("places", "creates")
 
_check(
    save_artifact(PUML_V2, "arch.puml", relative_path="docs/Time_2_Design/diagrams/arch.puml"),
    expect_success=True,
    label="Segunda escrita de arch.puml → deve criar _v2 no staging",
)
_check(
    list_versions("docs/Time_2_Design/diagrams/arch.puml"),
    expect_success=True,
    label="Listar versões de arch.puml",
)
 
# ═════════════════════════════════════════════════════════════════════════════
# BLOCO 4 — Promoção staging → destino oficial
# ═════════════════════════════════════════════════════════════════════════════
 
_header("BLOCO 4 — Promoção de staging para repositório oficial")
 
# Promoção SEM aprovação (deve bloquear)
_check(
    promote_artifact("flow.mmd", approved_by=""),
    expect_success=False,
    label="Promoção sem approved_by (deve bloquear)",
)
_check(
    promote_artifact("flow.mmd", approved_by="   "),
    expect_success=False,
    label="Promoção com approved_by em branco (deve bloquear)",
)
 
# Promoção COM aprovação (deve funcionar)
_check(
    promote_artifact("flow.mmd", approved_by="human:joao"),
    expect_success=True,
    label="Promoção de flow.mmd com aprovação",
)
_check(
    promote_artifact("adr-001.md", approved_by="human:maria"),
    expect_success=True,
    label="Promoção de adr-001.md com aprovação",
)
 
# ═════════════════════════════════════════════════════════════════════════════
# BLOCO 5 — Lock
# ═════════════════════════════════════════════════════════════════════════════
 
_header("BLOCO 5 — Verificação de lock")
 
_check(
    check_lock("docs/Time_2_Design/diagrams/arch.puml"),
    expect_success=True,
    label="Verificar lock (deve estar livre após operação)",
)
 
# ═════════════════════════════════════════════════════════════════════════════
# Resumo final
# ═════════════════════════════════════════════════════════════════════════════
 
total = pass_count + fail_count
print(f"\n{BOLD}{'═'*64}{RESET}")
print(f"{BOLD}  RESULTADO FINAL: {pass_count}/{total} casos corretos{RESET}")
if fail_count == 0:
    print(f"  {GREEN}{BOLD}✅ DoD aprovado — todos os casos passaram.{RESET}")
else:
    print(f"  {RED}{BOLD}❌ {fail_count} caso(s) falharam — revisar implementação.{RESET}")
print(f"{BOLD}{'═'*64}{RESET}\n")
 
# Limpa diretório temporário
import shutil
shutil.rmtree(_TEMP_ROOT, ignore_errors=True)
 
sys.exit(0 if fail_count == 0 else 1)