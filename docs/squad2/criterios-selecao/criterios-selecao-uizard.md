# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Uizard |
| **Versão (se aplicável):** | Autodesigner 1.5 (2.0 pago) |
| **URL oficial para acesso à ferramenta/documentação:** | https://uizard.io/ |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Danilo Sucupira Galvão |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

O Uizard é uma plataforma de prototipação rápida impulsionada por IA generativa multimodal. Ela permite que usuários transformem descrições textuais (prompts) ou imagens de telas(prints) em designs de interface (UI) editáveis e de alta fidelidade. Além do design visual, a ferramenta oferece a capacidade de exportar os componentes gerados para código Front-end (React/CSS). É destinada a engenheiros de software, gerentes de produto e fundadores que precisam validar requisitos visuais rapidamente sem depender de designers especializados.

> _[Ferramenta focada em Design Generativo e transição Design-to-Code]_  
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):** - ☑ Requisitos (Elicitação e Validação)
- ☑ Projeto/Arquitetura (Design de Interface)
- ☑ Implementação (Geração de Frontend)
- ☐ Testes  
- ☐ Integração/CI-CD  
- ☐ Manutenção/Evolução  
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
  *Atua primordialmente no Design de Software (UI/UX) e parcialmente na Implementação (geração de código).*
- A atuação cobre atividades centrais da fase? Quais? 
  *Sim, cobre a prototipação, validação com usuário e codificação inicial da interface.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):** - ☑ Geração automática (Texto-para-UI)
- ☐ Sugestão/recomendação  
- ☑ Análise inteligente (Visão Computacional para ler rascunhos)
- ☐ Automação baseada em IA  
- ☑ Outro: Imagem-para-Código

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?  
  *Sim, o core da ferramenta é o "Autodesigner" e o "Wireframe Scanner".*
- Que capacidades “inteligentes” foram observadas na prática?  
  *Capacidade de gerar telas com qualidade, editar e interpretar prints e converter em componentes digitais estruturados.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
  *Desenho vetorial manual de componentes padrão (botões, inputs) e estilização CSS inicial.*
- O ganho de produtividade foi significativo ou marginal?  
  *Significativo. Reduz horas de design no Figma para minutos de geração.*
- Foi necessário muito retrabalho/revisão manual?    
  *Moderado. O layout sai pronto, mas ajustes finos de alinhamento são necessários.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):** - ☑ Qualidade dos requisitos (Visualização imediata reduz ambiguidade)
- ☑ Qualidade do design (Aplica padrões modernos automaticamente)
- ☐ Qualidade do código  
- ☐ Qualidade dos testes  
- ☐ Qualidade da documentação  
- ☐ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?  
  *Evita a criação de interfaces "amadoras" por desenvolvedores sem conhecimento em design.*
- Houve melhoria perceptível na qualidade do artefato gerado?  
  *Visualmente sim. Em termos de código, o impacto é neutro (código funcional, mas básico).*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☐ Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- ☑ Comunidade ativa / relatos de uso  
- ☐ Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
  *Design Generativo e Prototipação Multimodal.*
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  
  *Sim. A maioria das ferramentas foca em código (IDE) ou chat. Esta foca em interface visual.*
- Há outras ferramentas muito similares já avaliadas?  
  *Uma ferramenta muito parecida é o Figma, que possui integração com IA.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- ☐ Pode introduzir erros críticos  
- ☐ Pode gerar resultados enganosos  
- ☐ Dependência excessiva de IA  
- ☑ Outros: *Vendor Lock-in (formatos proprietários) e geração de código não-otimizado.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- **Multimodalidade:** Única ferramenta avaliada capaz de converter imagens (prints) em software digital.
- **Velocidade de Validação:** Permite fechar requisitos com stakeholders mostrando o produto final simulado em minutos.
- **Exportação de Código:** Gera React/CSS utilizável, transpondo a barreira entre Design e Implementação.
 
### **Pontos fracos (bullet points)**
- **Qualidade do Código:** O código gerado é visualmente fiel, mas estruturalmente pobre (hardcoded, pouca componentização lógica).
- **Isolamento:** Não se conecta a lógicas de backend ou APIs reais durante a prototipação.

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☑ Incluir ☐ Incluir com ressalvas ☐ Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):** > _[N/A - Ferramenta incluída]_  

---

## **6) Evidências Anexas (opcional)**
- Links: [Uizard Autodesigner Blog](https://uizard.io/blog/)


---