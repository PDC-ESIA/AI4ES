# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Gpt 4o |
| **Versão (se aplicável):** |4o|
| **URL oficial para acesso à ferramenta/documentação:** |https://openai.com/pt-BR/index/hello-gpt-4o/ |
| **Data da avaliação:** |19/01/2026 |
| **Avaliador:** |Matheus Augusto de Paula Soares |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> O propósito geral do GPT 4o é apoiar na geraçãio, análise e compreensão de conteúdo textual, código e outros artefatos digitais. Ele é destinado para diversos públicos sem um em específico. Foi testado na resolução de um exercício de programação.
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):**  
- [x] Requisitos  
- [x] Projeto/Arquitetura  
- [x] Implementação  
- [x] Testes  
- [ ] Integração/CI-CD  
- [x] Manutenção/Evolução  
- [ ] Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita? 
> Requisitos, projeto, implementação, testes e manutenção. 
- A atuação cobre atividades centrais da fase? Quais? 
> Elicitação e refinamento de requisitos, sugestão de arquiteturas, geração e revisão de código, criação de casos de teste e apoio à manutenção evolutiva.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- [ ] Geração automática  
- [ ] Sugestão/recomendação  
- [x] Análise inteligente  
- [ ] Automação baseada em IA  
- [ ] Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?  
> Sim
- Que capacidades “inteligentes” foram observadas na prática?  
> N/A

**Atende ao critério?** [ ] Sim [x] Parcial [ ] Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
> Escrita inicial de código, documentação técnica e criação de testes unitários.
- O ganho de produtividade foi significativo ou marginal?  
> Significativo
- Foi necessário muito retrabalho/revisão manual?   
> Moderadamente 

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- [x] Qualidade dos requisitos
- [ ] Qualidade do design
- [x] Qualidade do código  
- [x] Qualidade dos testes  
- [x] Qualidade da documentação  
- [x] Consistência/detecção de erros  
- [ ] Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?
> A ferramenta pode identificar erros ao ser informado do código que foi escrito.  
- Houve melhoria perceptível na qualidade do artefato gerado?  
> Sim.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível  
- [x] Tutoriais/exemplos disponíveis  
- [ ] Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- [ ] Comunidade ativa / relatos de uso  
- [x] Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
> A ferramenta pode apoiar em muitas categorias do SDLC.
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas? 
> Sim. 
- Há outras ferramentas muito similares já avaliadas?  
> Sim.

**Atende ao critério?** [ ] Sim [x] Parcial [ ] Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- [x] Pode introduzir erros críticos  
- [x] Pode gerar resultados enganosos  
- [x] Dependência excessiva de IA  
- [ ] Outros: ___________

**Atende ao critério?** [ ] Sim [x] Parcial [ ] Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
-  Tempo para solucionar: 5 segundos
-  Tempo médio de execução da solução: 1,8ms
 
### **Pontos fracos (bullet points)**
-   Uso de Regex, o que dificulta a leitura do código.

---

## **5) Decisão Final de Inclusão**

**Decisão:** [x] Incluir [ ] Incluir com ressalvas [ ] Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):**  
> _[Inserir justificativa]_  

---

## **6) Evidências Anexas (opcional)**
- Links:  
- Arquivos gerados:  
```java
function detectBruteForce(logs) {
const failureCounts = {}; // Tracks consecutive failures
const suspiciousIPs = new Set();

logs.forEach(log => {
    const [, ip, action] = log.match(/^([\d.]+) (LOGIN_\w+)/);
    
    if (action === "LOGIN_FAIL") {
        failureCounts[ip] = (failureCounts[ip] || 0) + 1;
        if (failureCounts[ip] === 3) {
            suspiciousIPs.add(ip);
        }
    } else if (action === "LOGIN_SUCCESS") {
        failureCounts[ip] = 0; // Reset on success
    }
});

return Array.from(suspiciousIPs).sort();
}
```
---
