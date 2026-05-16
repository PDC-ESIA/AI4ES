from datetime import datetime, timezone
from pathlib import Path
import re


DOUBT_DIR = Path(__file__).resolve().parent.parent / "doubt_artifacts"

DOUBT_ARTEFACT_TEMPLATE = """# DOUBT ARTEFACT | [ID-DA-000]

## 1. Identificação Técnica
- **ID do Artefato:** `{{artifact_id}}`
- **Timestamp:** `{{timestamp}}`
- **Agente Responsável:** `{{agent_name}}`
- **Módulo/Ferramenta:** `{{module_name}}`
- **Severidade:** 🔴 Crítico | 🟠 Anomalia Lógica | 🟡 Contexto | 🟣 Segurança

## 2. Gatilho de Pausa (Diagnóstico de Falha do Agente)
> **[ Falhas de Execução & Limites ]**
> - [ ] **Erro de Sintaxe/Runtime:** Código gerado falhou na compilação/execução.
> - [ ] **Timeout / Indisponibilidade:** API ou Tool externa não respondeu.
> - [ ] **Rate Limit / Cota Mínima:** Limite de requisições do modelo atingido (429).
> - [ ] **Estouro de Tokens:** Limite da janela de contexto excedido.
>
> **[ Anomalias de Lógica & Alucinação ]**
> - [ ] **Assinatura Inválida:** Agente inventou parâmetros ou ferramentas (Alucinação).
> - [ ] **Loop Infinito de Tools:** Agente preso em ciclo de repetição sem progresso.
> - [ ] **Falha de Parseamento:** Saída do modelo fora do formato exigido (ex: não é JSON válido).
>
> **[ Intenção, Contexto & Segurança ]**
> - [ ] **Ambiguidade / Falta de Contexto:** Instrução imprecisa ou falta de histórico/regras.
> - [ ] **Violação de Guardrail / Prompt Injection:** Tentativa de burlar regras do *System Prompt*.
> - [ ] **Risco de Dados (PII):** Operação expõe ou requer dados sensíveis não autorizados.

## 3. Evidência
**Trecho, Prompt ou StackTrace:**

{{suspect_code_or_prompt}}

**Análise / Motivo da Interrupção:**
> `{{reason_for_invalidation}}`

## 4. Contexto de Execução
- **Artefato de Entrada:** `{{input_artifact_name}}`
- **Ação Realizada:** `{{action_attempted}}`
- **Resposta Bruta (Raw Output):** `{{system_raw_response}}`

## 5. Próximos Passos (Resolução)
- [ ] Ajustar System Prompt ou In-Context Learning (Few-shot).
- [ ] Implementar retry automático ou truncamento de tokens.
- [ ] Corrigir Tool/API ou refinar esquema de parâmetros (Pydantic/JSON Schema).
- [ ] Esclarecer intenção com o usuário/coordenação.

**Gerado automaticamente via ADK Tool v1.0**
*Status da Validação (Coordenação Técnica): [ ] Aprovado | [ ] Reprovado*
"""


def _safe_file_part(value: str) -> str:
    """Sanitiza string para uso em nome de arquivo.

    Args:
        value: String a ser sanitizada.

    Returns:
        str: String segura para nomes de arquivo.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return cleaned.strip("_") or "SEM_ID"


def _text(value: str, fallback: str = "N/A") -> str:
    """Retorna valor como string ou fallback se None.

    Args:
        value: Valor a converter.
        fallback: Valor padrão se value for None.

    Returns:
        str: String representando o valor.
    """
    return str(value) if value is not None else fallback


def gerar_doubt_artifact(
    reason_for_invalidation: str,
    artifact_id: str = "ID-DA-000",
    module_name: str = "action_planner",
    suspect_code_or_prompt: str = "N/A",
    input_artifact_name: str = "N/A",
    action_attempted: str = "Planejamento de ação",
    system_raw_response: str = "N/A",
) -> dict:
    """Gera artefato de dúvida para documentação de bloqueios do agente.

    Args:
        reason_for_invalidation: Motivo da invalidação/bloqueio.
        artifact_id: Identificador único do artefato.
        module_name: Módulo/ferramenta que gerou o bloqueio.
        suspect_code_or_prompt: Código ou prompt que causou a dúvida.
        input_artifact_name: Nome do artefato de entrada.
        action_attempted: Ação que estava sendo executada.
        system_raw_response: Resposta bruta do sistema.

    Returns:
        dict: Status e path do artefato gerado.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_artifact_id = _safe_file_part(artifact_id)
    DOUBT_DIR.mkdir(parents=True, exist_ok=True)

    content = (
        DOUBT_ARTEFACT_TEMPLATE.replace("{{artifact_id}}", _text(artifact_id))
        .replace("{{timestamp}}", timestamp)
        .replace("{{agent_name}}", "action_planner")
        .replace("{{module_name}}", _text(module_name))
        .replace("{{suspect_code_or_prompt}}", _text(suspect_code_or_prompt))
        .replace("{{reason_for_invalidation}}", _text(reason_for_invalidation))
        .replace("{{input_artifact_name}}", _text(input_artifact_name))
        .replace("{{action_attempted}}", _text(action_attempted))
        .replace("{{system_raw_response}}", _text(system_raw_response))
    )

    path = DOUBT_DIR / f"Doubt_Artefact_{safe_artifact_id}_{timestamp}.md"
    path.write_text(content, encoding="utf-8")

    return {
        "status": "ok",
        "artifact_id": artifact_id,
        "path": str(path),
    }
