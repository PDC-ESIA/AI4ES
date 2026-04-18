import os
from datetime import datetime, timezone
from pathlib import Path

class DoubtArtifactGenerator:
    
    # Template 
    TEMPLATE = """# DOUBT ARTEFACT | [{artifact_id}]

## 1. Identificação Técnica
- **ID do Artefato:** `{artifact_id}`
- **Timestamp:** `{timestamp}`
- **Agente Responsável:** `qa_agente`
- **Módulo/Ferramenta:** `{module_name}`
- **Severidade:** 🔴 Crítico | 🟠 Anomalia Lógica | 🟡 Contexto | 🟣 Segurança

## 2. Gatilho de Pausa (Diagnóstico de Falha do Agente)
> **[ Falhas de Execução & Limites ]**
> - [{check_syntax}] **Erro de Sintaxe/Runtime:** Código gerado falhou na compilação/execução.
> - [{check_timeout}] **Timeout / Indisponibilidade:** API ou Tool externa não respondeu.
> - [{check_rate_limit}] **Rate Limit / Cota Mínima:** Limite de requisições do modelo atingido (429).
> - [{check_token_limit}] **Estouro de Tokens:** Limite da janela de contexto excedido.
> 
> **[ Anomalias de Lógica & Alucinação ]**
> - [{check_signature}] **Assinatura Inválida:** Agente inventou parâmetros ou ferramentas (Alucinação).
> - [{check_loop}] **Loop Infinito de Tools:** Agente preso em ciclo de repetição sem progresso.
> - [{check_parse_error}] **Falha de Parseamento:** Saída do modelo fora do formato exigido (ex: não é JSON válido).
> 
> **[ Intenção, Contexto & Segurança ]**
> - [{check_context}] **Ambiguidade / Falta de Contexto:** Instrução imprecisa ou falta de histórico/regras.
> - [{check_guardrail}] **Violação de Guardrail / Prompt Injection:** Tentativa de burlar regras do *System Prompt*.
> - [{check_security}] **Risco de Dados (PII):** Operação expõe ou requer dados sensíveis não autorizados.

## 3. Evidência
**Trecho, Prompt ou StackTrace:**

{suspect_code_or_prompt}

**Análise / Motivo da Interrupção:**
> `{reason_for_invalidation}`

## 4. Contexto de Execução
- **Artefato de Entrada:** `{input_artifact_name}`
- **Ação Realizada:** `{action_attempted}`
- **Resposta Bruta (Raw Output):** `{system_raw_response}`

## 5. Próximos Passos (Resolução)
- [ ] Ajustar System Prompt ou In-Context Learning (Few-shot).
- [ ] Implementar retry automático ou truncamento de tokens.
- [ ] Corrigir Tool/API ou refinar esquema de parâmetros (Pydantic/JSON Schema).
- [ ] Esclarecer intenção com o usuário/coordenação.

---
**Gerado automaticamente via ADK Tool v1.0**
*Status da Validação (Coordenação Técnica): [ ] Aprovado | [ ] Reprovado*
"""

    @classmethod
    def generate(cls, id_artefato: str, motivo: str, caminho_base: Path, trigger_type: str = "loop") -> str:
        # 1. Lógica de Caminho 
        doubt_dir = caminho_base.parent / "doubt_artifacts"
        doubt_dir.mkdir(parents=True, exist_ok=True)

        # 2. Timestamps e Nome do Arquivo
        timestamp_file = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        timestamp_display = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        nome_arquivo = f"Doubt_Artifact_{id_artefato}_{timestamp_file}.md"
        caminho_final = doubt_dir / nome_arquivo

        # 3. Preparação dos dados
        data = {
            "artifact_id": id_artefato,
            "timestamp": timestamp_display,
            "module_name": "qa_agent / pytest_runner",
            "reason_for_invalidation": motivo,
            "suspect_code_or_prompt": "Verificar logs do pytest_runner",
            "input_artifact_name": "N/A",
            "action_attempted": "Execução de testes",
            "system_raw_response": "ERR_LOOP detectado"
        }

        # 4. Lógica dos Checkboxes
        triggers = [
            "syntax", "timeout", "rate_limit", "token_limit", 
            "signature", "loop", "parse_error", "context", "guardrail", "security"
        ]
        
        for trigger in triggers:
            data[f"check_{trigger}"] = "x" if trigger_type == trigger else " "
            
        # 5. Renderização e Escrita final
        try:
            content = cls.TEMPLATE.format(**data)
            caminho_final.write_text(content, encoding="utf-8")
        except KeyError as e:
            # Caso falte alguma chave no dicionário 'data'
            print(f"Erro ao gerar template: Chave faltando {e}")
            raise

        return str(caminho_final)