# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | GitHub Copilot |
| **Versão (se aplicável):** | |
| **URL oficial para acesso à ferramenta/documentação:** | https://github.com/copilot |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Matheus Augusto de Paula Soares |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> O propósito do GitHub copilot é auxiliar desenvolvedores na tarefa de escrita de código. A ferramenta foi testada de forma limitada em forma de um experimento controlado de desenvolvimento de uma calculadora de IMC no terminal utilizando como linguagem de programação Java e como IDE o IntelliJ.  
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):**  
- [ ] Requisitos  
- [ ] Projeto/Arquitetura  
- [x] Implementação  
- [x] Testes  
- [ ] Integração/CI-CD  
- [x] Manutenção/Evolução  
- [ ] Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
> Implementação e manutenção.
- A atuação cobre atividades centrais da fase? Quais? 
> Escrita e sugestão de códigos (incluindo testes)

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- [x] Geração automática  
- [x] Sugestão/recomendação  
- [x] Análise inteligente  
- [ ] Automação baseada em IA  
- [ ] Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?  
> Sim
- Que capacidades “inteligentes” foram observadas na prática?  
> Geração e sugestão de código com base no já escrito pelo desenvolvedor.

**Atende ao critério?** [ ] Sim [ ] Parcial [ ] Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
> Codificação
- O ganho de produtividade foi significativo ou marginal?  
> Significativo
- Foi necessário muito retrabalho/revisão manual?    
> Não

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- [ ] Qualidade dos requisitos
- [ ] Qualidade do design
- [x] Qualidade do código  
- [x] Qualidade dos testes  
- [ ] Qualidade da documentação  
- [x] Consistência/detecção de erros  
- [ ] Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?
> Sim, ao entender o que está sendo feito, a ferramentagera sugestões de códigos para que a tarefa seja executada de forma mais rápida e, evitando assim, erros.  
- Houve melhoria perceptível na qualidade do artefato gerado?  
> Sim.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível  
- [x] Tutoriais/exemplos disponíveis  
- [x] Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- [x] Comunidade ativa / relatos de uso  
- [ ] Estudos acadêmicos ou relatos industriais 

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
> Geração de código.
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?
> Sim  
- Há outras ferramentas muito similares já avaliadas? 
> Sim 

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- [x] Pode introduzir erros críticos  
- [x] Pode gerar resultados enganosos  
- [x] Dependência excessiva de IA  
- [ ] Outros: ___________

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- Tempo para solucionar: 01 minuto e 21 segundos
 
### **Pontos fracos (bullet points)**
-  Nada a declarar

---

## **5) Decisão Final de Inclusão**

**Decisão:** [x] Incluir [ ] Incluir com ressalvas [ ] Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):**  

---

## **6) Evidências Anexas (opcional)**
- Links:  
- Arquivos gerados:  

```Java

    void main() {
    Scanner scanner = new Scanner(System.in);

    float wheight, height, IMC;

    System.out.print("Digite o seu peso (kg): ");

    wheight = scanner.nextFloat();

    System.out.print("Digite a sua altura (m): ");

    height = scanner.nextFloat();

    IMC = wheight / (height * height);

    System.out.printf("O seu IMC é: %.2f\n", IMC);

}

    
```

---
