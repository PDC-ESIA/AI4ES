> ### 🔍 Checklist de Validação Rápida (Anti-Alucinação)
> **1. Importações:** Os pacotes e classes existem na doc oficial e no `requirements.txt`?
> **2. Assinaturas:** Os nomes das funções da equipe estão certos? A IA inventou parâmetros (ex: `auto_clean`, `force`)?
> **3. Lógica:** A IA usou caminhos absurdos (ex: recursão infinita) ou mascarou erros (usando `try...except` que força o sucesso)?
> **4. Validação (Asserts):** O `assert` está validando o resultado real do sistema ou apenas testando variáveis fixas/vazias (ex: `assert True`)?

# DOUBT ARTEFACT | [ID-DA-000]

## 1. Identificação Técnica
- **ID do Artefato:** `{{artifact_id}}`
- **Timestamp:** `{{timestamp}}`
- **Agente Responsável:** `qa_agente`
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


**Artefatos relacionados**
Artefatos que tenham relacao com o que esta sendo relatadp
