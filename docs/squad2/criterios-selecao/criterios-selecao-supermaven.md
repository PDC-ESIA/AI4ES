# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Supermaven |
| **Versão (se aplicável):** | 1.0 |
| **URL oficial para acesso à ferramenta/documentação:** | https://supermaven.com |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Danilo Sucupira Galvão |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

O Supermaven é um assistente de codificação de baixíssima latência, focado em autocompletar código e responder dúvidas via chat dentro da IDE (VS Code, JetBrains, etc). Seu principal diferencial técnico é uma janela de contexto de 1 milhão de tokens, permitindo que a IA "leia" e compreenda a base de código inteira do projeto instantaneamente, sem a necessidade de RAG complexo. É destinada a desenvolvedores de software para as fases de construção, manutenção e refatoração.

> _[Ferramenta focada em Construção e Manutenção com destaque para Large Context Window]_  
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):** - ☐ Requisitos  
- ☐ Projeto/Arquitetura  
- ☑ Implementação (Codificação ativa)
- ☑ Testes (Geração de unit tests)
- ☐ Integração/CI-CD  
- ☑ Manutenção/Evolução (Refatoração e entendimento de legado)
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
  *Construção de Software (escrita de código) e Manutenção.*
- A atuação cobre atividades centrais da fase? Quais? 
  *Sim. Cobre a escrita de algoritmos, uso de APIs internas e refatoração.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):** - ☑ Geração automática (Code completion)
- ☑ Sugestão/recomendação  
- ☑ Análise inteligente (In-context Learning sobre o repo inteiro)
- ☐ Automação baseada em IA  
- ☐ Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?  
  *Sim, utiliza o modelo proprietário "Babble" e Claude 3.5 Sonnet.*
- Que capacidades “inteligentes” foram observadas na prática?  
  *Capacidade de sugerir adições corretas com base em arquivos que não estavam abertos.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
  *Digitação de boilerplate, busca por definições de funções em outros arquivos e escrita de testes unitários.*
- O ganho de produtividade foi significativo ou marginal?  
  *Significativo. Estimativa de 40% de redução no tempo de digitação.*
- Foi necessário muito retrabalho/revisão manual?    
  *Baixo. A precisão sintática é alta devido ao contexto estendido.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):** - ☐ Qualidade dos requisitos
- ☐ Qualidade do design
- ☑ Qualidade do código (Consistência de estilo)
- ☑ Qualidade dos testes  
- ☑ Qualidade da documentação (Docstrings automatizados)
- ☐ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?  
  *Sim, evita erros de importação e tipagem ao conhecer as definições do projeto.*
- Houve melhoria perceptível na qualidade do artefato gerado?  
  *O código gerado adere estritamente aos padrões arquiteturais já existentes no projeto.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☑ Integração com ferramentas comuns (VS Code, JetBrains, Neovim)  
- ☐ Comunidade ativa / relatos de uso  
- ☐ Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
  *Assistentes de Codificação Neural com Contexto Infinito (Long Context).*
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  
  *Sim. Diferencia-se dos Copilots tradicionais pela arquitetura de memória/contexto.*
- Há outras ferramentas muito similares já avaliadas?  
  *Não.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- ☐ Pode introduzir erros críticos  
- ☐ Pode gerar resultados enganosos  
- ☐ Dependência excessiva de IA  
- ☑ Outros: *Privacidade de Dados (Código é processado na nuvem, sem opção local).*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- **Janela de Contexto (1M tokens):** Elimina a necessidade de "selecionar" arquivos para o contexto; a IA vê tudo.
- **Velocidade:** Latência extremamente baixa, tornando o autocomplete fluido.
- **Adaptação:** Aprende o estilo do projeto (indentação, nomes de variáveis) instantaneamente.
 
### **Pontos fracos (bullet points)**
- **Privacidade:** Inviável para projetos com *compliance* rígido que proíbem envio de código para terceiros.
- **Ferramentas Auxiliares:** Menos recursos de "Agente" (criação de arquivos, terminais) do que concorrentes como Cursor.
- **Recursos pagos:** O chat com a IA é um recurso pago, ficando limitado ao recurso de completar códigos.

---

## **5) Decisão Final de Inclusão**

**Decisão:**  ☐ Incluir ☐ Incluir com ressalvas ☑ Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):** > A ferramenta não deve ser incluída devido à sua limitação causada pelo chat com a IA ser um recurso pago, o que impossibilita que ela seja corretamente analisada e avaliada de acordo com um protocolo padrão para diferentes ferramentas e também pelo fato de que o Supermaven, como anunciado no final de 2025, não receberá mais atualizações, apesar de continuar sendo possível utilizar a ferramenta.

---

## **6) Evidências Anexas (opcional)**
- Links: [Supermaven Technical Blog](https://supermaven.com/blog)

---