#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          | GPT4o                                                                          |
| **Fabricante / Comunidade**     | Open AI                                                                        |
| **Site oficial / documentação** | https://openai.com/pt-BR/index/hello-gpt-4o/                                                                               |
| **Tipo de ferramenta**          | LLM Geral |
| **Licença / acesso**            | Comercial                                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM                         |
| **Nome do Modelo**                  | GPT 4o |
| **Versão**                          | 4o                                                             |
| **Tamanho (nº de parâmetros)**      | Não divulgado oficialmente pela OpenAI                                                |
| **Acesso**                          | API comercial / Site oficial                          |
| **Suporte a Fine-tuning**           | Sim (via API, com restrições)                    |
| **Suporte a RAG**                   | Sim (externo, via embeddings + ferramentas)                                                     |
| **Métodos de prompting suportados** | Não divulgado                            |
| **Ferramentas adicionais**          | Visão, análise de imagens, leitura de documentos, execução de código, voz    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Cloud                 |
| **Infraestrutura utilizada no teste** | (GPU, CPU, RAM ou serviço utilizado)    |
| **Custos (quando aplicável)**         | De R$99,90 a R$999,90/mês (planos ChatGPT) + cobrança por token na API |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo, descreva:

* **O que a ferramenta faz**
* **Como faz**
* **Exemplos / evidências**
* **Limitações observadas**

Use N/A quando não aplicável.

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              | Suporta               | Interpreta requisitos a partir de linguagem natural, perguntas abertas e exemplos                         |
| Análise                 | Suporta               | Identifica inconsistências, ambiguidades e regras implícitas                         |
| Priorização             | Suporta               | Sugere backlog, valor vs. esforço                         |
| Modelagem               | Suporta               | Gera UML textual, entidades, fluxos e modelos conceituais                         |
| Validação / Verificação | Parcialmente          | Depende de validação humana; não executa requisitos em ambiente real                         |
| Documentação            | Parcialmente          | Gera documentação, mas sem controle formal de versionamento                         |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Suporta               | Sugestão de arquiteturas em camadas, hexagonal, microserviços                         |
| Decisões arquiteturais           | Suporta               | Justifica decisões com base em requisitos não funcionais                         |
| Avaliação de trade-offs          | Suporta               | Justifica decisões com base em requisitos não funcionais                         |
| Uso de padrões arquiteturais     | Suporta               | MVC, Clean Architecture, Event-Driven, CQRS                         |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Suporta               | Factory, Strategy, Observer, Adapter, SOLID                         |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Suporta               | Código funcional, legível e alinhado a boas práticas                         |
| Refatoração       | Suporta               | Melhoria de legibilidade, redução de complexidade ciclomática                         |
| Detecção de bugs  | Suporta               | Identificação de erros lógicos e edge cases                         |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Suporta               | Unitários, integração e testes baseados em casos de uso                         |
| Execução de testes automatizados                 | Não Suporta           | Somente via ambientes externos (ex.: Code Interpreter, CI humano)                         |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Não suporta           | Integração indireta apenas via scripts externos                         |
| Automação                         | Não suporta           | Não executa pipelines autonomamente                         |
| Monitoramento                     | Não suporta           | Sem observabilidade nativa                         |
| Documentação técnica automatizada | Não suporta           | Pode gerar docs, mas não publica ou mantém automaticamente                         |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Não suporta           | Sugere correções, mas não aplica em produção                         |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Suporta               | Roadmaps, cronogramas                         |
| Execução                            | Parcialmente          | Apoio conceitual, sem execução real                         |
| Controle                            | Parcialmente          | Sugere métricas e indicadores                         |
| Encerramento                        | Parcialmente          | Checklists e relatórios finais                         |
| Gestão de riscos                    | Parcialmente          | Identificação e mitigação teórica                         |
| Estimativas (tempo, custo, esforço) | Parcialmente          | Estimativas heurísticas, não contratuais                         |
| Medição                             | Parcialmente          | KPIs sugeridos, sem coleta automática                         |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐             | O GPT-4o apresenta alto grau de correção sintática e semântica na maioria das respostas, especialmente em problemas bem definidos. No experimento de detecção de brute force, a solução gerada foi correta, passou por todos os testes automatizados e respeitou integralmente as regras do enunciado.             |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            | As respostas vão além do “como fazer”, explicando por que determinada abordagem é adequada, o que é especialmente relevante para decisões técnicas e arquiteturais.            |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | No experimento apresentado, o GPT-4o compreendeu corretamente o conceito de falhas consecutivas por IP e aplicou o reset de contagem após sucesso, sem ambiguidade.            |
| Clareza                             | ⭐⭐⭐⭐⭐            | Isso reduz o esforço cognitivo do desenvolvedor e facilita revisões de código, onboarding e documentação.            |
| Aderência às melhores práticas      | ⭐⭐⭐⭐             | Em alguns casos, pode priorizar clareza em detrimento de micro-otimizações, o que é desejável na maioria dos contextos, mas pode não atender cenários de alta performance sem ajuste humano.            |
| Consistência entre respostas        | ⭐⭐⭐⭐             | Mudanças sutis no prompt podem gerar abordagens diferentes para o mesmo problema, exigindo padronização de prompts em ambientes corporativos.            |
| Ocorrência de alucinações           | Baixa                  | Alucinações não foram observadas durante o experimento empirico            |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

Resolução de um exercício do site codewars.

Enunciado:

You're analyzing authentication logs. Each log entry is a string like:

```PowerShell
192.168.1.1 LOGIN_FAIL user=admin
192.168.1.1 LOGIN_SUCCESS user=admin
10.0.0.5 LOGIN_FAIL user=root
```

An IP is suspicious if it has 3 or more consecutive failures without a success in between. Return a list of suspicious IPs, sorted alphabetically.
        
```PowerShell
logs = [
    "192.168.1.1 LOGIN_FAIL user=admin",
    "192.168.1.1 LOGIN_FAIL user=admin",
    "192.168.1.1 LOGIN_FAIL user=root",
    "10.0.0.5 LOGIN_FAIL user=test",
    "10.0.0.5 LOGIN_SUCCESS user=test"
]
detect_brute_force(logs)  # ["192.168.1.1"]
```
        
The 10.0.0.5 IP had a failure then a success, so its streak reset. The 192.168.1.1 IP hit 3 failures in a row - busted. Only respond with a list of the suspicious IPs.

A success resets that IP's failure count to zero. Empty list returns empty list.

PS. You do not need to validate the IP addresses.

### ● Resultados quantitativos

* Com IA
    * Tempo para solucionar: 5 segundos
    * Tempo médio de execução da solução: 1,8ms
    * Cobertura de testes: Aprovado em todos os testes

* Sem IA
    * Tempo para solucionar: 43 minutos
    * Tempo médio de execução da solução: 2,6ms
    * Cobertura de testes: Aprovado em todos os testes

### ● Exemplos (copie trechos de código, respostas etc.)

* Código com IA:

    ```JavaScript
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

* Código sem IA:

    ```JavaScript
    function detectBruteForce(logs){
    const IPs = {};
    const errors = []
    logs.forEach(element => {
      const IP = element.split(" ")[0];
      const result = element.split(" ")[1];
      if(!Object.hasOwn(IPs, IP) && result == "LOGIN_FAIL"){
        Object.assign(IPs, {[IP]: 1});
      }else if(result == "LOGIN_FAIL"){
          Object.assign(IPs, {[IP]: Object.getOwnPropertyDescriptor(IPs, IP).value + 1});
      } else if(result == "LOGIN_SUCCESS" && Object.getOwnPropertyDescriptor(IPs, IP).value < 3){
          Object.assign(IPs, {[IP]: 0});
      }
    })
    logs.forEach(element => {
      const IP = element.split(" ")[0];
      if(!errors.includes(IP)){
         Object.getOwnPropertyDescriptor(IPs, IP).value >= 3 && errors.push(IP)
      }
    })
    return errors.sort();
    }
    ```

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Alta produtividade em atividades cognitivas complexas
* Excelente contextualização de código e requisitos
* Forte aderência a boas práticas de engenharia
* Suporte multimodal (texto, código, imagem)
* Redução significativa de tempo de desenvolvimento (comprovado no experimento)

### **Limitações**

* Número de parâmetros e detalhes internos não divulgados
* Pode apresentar alucinações em domínios mal especificados
* Não substitui validação humana nem execução real
* Dependência total de infraestrutura cloud

#  **8. Riscos, Custos e Considerações de Uso**

* Dependência de fornecedor
* Custos recorrentes por uso intensivo
* Questões de privacidade e compliance (dados sensíveis exigem cautela)
* Impossibilidade de execução totalmente on-premises
* Fine-tuning e RAG limitados às políticas da OpenAI

---

#  **9. Conclusão Geral da Análise**

* Adequada para:
    * Engenharia de requisitos, design, arquitetura, codificação, testes e apoio à gestão de projetos.

* Deve ser evitada quando:
*   Há exigência de execução local, compliance rígido, ou automação totalmente autônoma.

* Maturidade técnica:
*   Alta — ferramenta consolidada, estável e amplamente utilizada em ambientes profissionais.

* Vale a pena para a organização?
*   Sim, especialmente como copiloto de engenharia, aumentando produtividade e qualidade, desde que usada com governança adequada.

---

#  **10. Referências e Links Consultados**

* OpenAI – GPT-4o
    * https://openai.com/pt-BR/index/hello-gpt-4o/
* OpenAI API Documentation
    * https://platform.openai.com/docs
* SWEBOK v3.0 – IEEE
* Benchmarks e experiências práticas (Codewars, testes empíricos)