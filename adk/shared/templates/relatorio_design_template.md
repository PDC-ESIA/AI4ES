# Relatório de Arquitetura — <HU-XXX, HU-YYY>

**Solicitante:** <Nome do solicitante>
**Data:** <YYYY-MM-DD>
**Gerado por:** Especialista Markdown — Agente MVP Time 2
**Status:** Em análise

---

## 1. Identificação das HUs

| HU | Stakeholder | Ação central | Critérios de aceite |
|----|-------------|--------------|---------------------|
| HU-XXX | <stakeholder> | <ação central em uma frase> | <critérios separados por `;`> |
| HU-YYY | <stakeholder> | <ação central em uma frase> | <critérios separados por `;`> |

---

## 2. Diagrama de Arquitetura

### HU-XXX — <título descritivo>

```<tipo_mermaid>
<conteúdo exato do arquivo .mmd aprovado, incluindo todos os participantes e relações>
```

### HU-YYY — <título descritivo>

```<tipo_mermaid>
<conteúdo exato do arquivo .mmd aprovado>
```

---

## 3. Decisões de Arquitetura

### Decisão 1 — <nome_curto>

**HUs cobertas:** HU-XXX, HU-YYY
**Decisão:** <alternativa escolhida>
**Justificativa:** <justificativa técnica em 2-3 frases>
**Reversibilidade:** <Alta / Média / Baixa>

| Alternativa | Prós | Contras |
|-------------|------|---------|
| <alternativa_A> | <prós> | <contras> |
| <alternativa_B> | <prós> | <contras> |
| <alternativa escolhida> ✓ | <prós> | <contras> |

---

## 4. Componentes

| Componente | Responsabilidade | Dependências |
|------------|-----------------|--------------|
| <nome> | <responsabilidade principal em uma frase> | <dependências separadas por `,` ou `—` se nenhuma> |

---

## 5. Bloqueios e Pendências

> Liste em ordem decrescente de severidade: 🔴 Alta → 🟡 Média → 🟢 Baixa.
> Se não houver bloqueios: substituir por **Nenhum.**

- 🔴 **<título do bloqueio>** — <descrição breve> → Doubt_Artifact: `<nome_do_arquivo.md>` *(categoria: Lacuna Funcional | Lacuna Arquitetural)*
- 🟡 **<título do bloqueio>** — <descrição breve>
- 🟢 **<título do bloqueio>** — <descrição breve>

---

## 6. Cobertura de HUs

> Declaração obrigatória de cobertura por HU. Gerada pelo design_architect e transcrita aqui pelo markdown_specialist.
> HUs bloqueadas aparecem como ❌ com referência ao Doubt_Artifact correspondente.

| HU | Atendida | Justificativa |
|----|----------|---------------|
| HU-XXX | ✅ | <componentes ou decisões que cobrem o fluxo desta HU> |
| HU-YYY | ❌ | <restrição ou lacuna que impediu cobertura> → Doubt_Artifact: `<nome_do_arquivo.md>` |

---

## 7. Gap Analysis — Lacunas Identificadas

> O que as HUs **não dizem** mas que impacta diretamente a arquitetura.
> Cada lacuna deve indicar sua categoria e o risco arquitetural associado.
> Se não houver lacunas: substituir por **Nenhuma lacuna identificada.**

| # | Lacuna | Categoria | Impacto Arquitetural | Ação Recomendada |
|---|--------|-----------|----------------------|------------------|
| 1 | <descrição objetiva do que está ausente> | Funcional \| Arquitetural | <decisão que fica em aberto ou componente que não pode ser definido> | Doubt_Artifact \| Assumir padrão \| Escalar para Time 1 |
| 2 | <descrição objetiva do que está ausente> | Funcional \| Arquitetural | <impacto> | <ação> |