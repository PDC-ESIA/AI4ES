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
| **Tamanho (nº de parâmetros)**      |                                                 |
| **Acesso**                          | API comercial / Site oficial                          |
| **Suporte a Fine-tuning**           | Sim                    |
| **Suporte a RAG**                   | Sim                                                     |
| **Métodos de prompting suportados** |                             |
| **Ferramentas adicionais**          |     |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Cloud                 |
| **Infraestrutura utilizada no teste** | (GPU, CPU, RAM ou serviço utilizado)    |
| **Custos (quando aplicável)**         | De R$99,90 a 999,90 por mês |

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
| Elicitação              | Suporta               |                          |
| Análise                 | Suporta               |                          |
| Priorização             | Suporta               |                          |
| Modelagem               | Suporta               |                          |
| Validação / Verificação | Parcialmente          |                          |
| Documentação            | Parcalmente           |                          |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Suporta               |                          |
| Decisões arquiteturais           | Suporta               |                          |
| Avaliação de trade-offs          | Suporta               |                          |
| Uso de padrões arquiteturais     | Suporta               |                          |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Suporta               |                          |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Suporta               |                          |
| Refatoração       | Suporta               |                          |
| Detecção de bugs  | Suporta               |                          |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Suporta               |                          |
| Execução de testes automatizados                 | Suporta               |                          |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Não suporta           |                          |
| Automação                         | Não suporta           |                          |
| Monitoramento                     | Não suporta           |                          |
| Documentação técnica automatizada | Não suporta           |                          |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Não suporta           |                          |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Suporta               |                          |
| Execução                            | Parcialmente          |                          |
| Controle                            | Parcialmente          |                          |
| Encerramento                        | Parcialmente          |                          |
| Gestão de riscos                    | Parcialmente          |                          |
| Estimativas (tempo, custo, esforço) | Parcialmente          |                          |
| Medição                             | Parcialmente          |                          |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐             |             |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            |             |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            |             |
| Clareza                             | ⭐⭐⭐⭐⭐            |             |
| Aderência às melhores práticas      | ⭐⭐⭐⭐             |             |
| Consistência entre respostas        | ⭐⭐⭐⭐             |             |
| Ocorrência de alucinações           | Média                  |             |

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

* Dependência de vendor
* Custos recorrentes
* Limitações em privacidade ou compliance
* Barreiras técnicas de adoção
* Dificuldades de execução local
* Restrições para fine-tuning ou RAG

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para quais atividades de ES?
* Em quais casos deve ser evitada?
* Em qual maturidade técnica ela se encontra?
* Vale a pena para a organização?

---

#  **10. Referências e Links Consultados**

* Documentação oficial
* Artigos
* Tutoriais
* Benchmarks independentes
