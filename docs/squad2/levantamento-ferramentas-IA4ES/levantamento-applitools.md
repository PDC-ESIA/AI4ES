#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          | Applitools                                                                      |
| **Fabricante / Comunidade**     | Applitools Ltd.                                                                 |
| **Site oficial / documentação** | https://applitools.com/docs/                                                    |
| **Tipo de ferramenta**          | Plataforma de testes visuais automatizados com suporte a IA                    |
| **Licença / acesso**            | Comercial (modelo SaaS, com período de trial)                                  |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | IA baseada em visão computacional e aprendizado de máquina   |
| **Nome do Modelo**                  | Visual AI (modelo proprietário da Applitools)                |
| **Versão**                          | Proprietária (versões não divulgadas publicamente)           |
| **Tamanho (nº de parâmetros)**      | Não divulgado                                                |
| **Acesso**                          | API comercial (cloud)                                        |
| **Suporte a Fine-tuning**           | Não (modelo fechado e gerenciado pelo fornecedor)            |
| **Suporte a RAG**                   | Não aplicável                                                |
| **Métodos de prompting suportados** | Não aplicável (não utiliza prompting textual como LLMs)      |
| **Ferramentas adicionais**          | SDKs para Selenium, Cypress, Playwright, Appium, WebdriverIO, Storybook |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                                                             |
| ------------------------------------- | --------------------------------------------------------------------- |
| **Onde roda?**                        | Cloud (infraestrutura da Applitools)                                  |
| **Infraestrutura utilizada no teste** | Execução local dos testes + processamento visual na nuvem da Applitools |
| **Custos (quando aplicável)**         | Gratuito ou US$ 969/mês (Starter)                                     |

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
| Elicitação              | N/A                   | N/A                      |
| Análise                 | N/A                   | N/A                      |
| Priorização             | N/A                   | N/A                      |
| Modelagem               | N/A                   | N/A                      |
| Validação / Verificação | Sim                   | Atua na verificação da interface contra um "contrato visual" (Baseline). Se o requisito mudar, a IA identifica o desvio. |
| Documentação            | N/A                   | N/A                      |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | N/A                   | N/A                      |
| Decisões arquiteturais           | N/A                   | N/A                      |
| Avaliação de trade-offs          | N/A                   | N/A                      |
| Uso de padrões arquiteturais     | N/A                   | N/A                      |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Sim                   | Garante a fidelidade do Design System. Observou-se que a IA aprende o padrão visual enviado na primeira rodada e o protege contra mudanças futuras. |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | N/A                   | N/A                      |
| Refatoração       | N/A                   | N/A                      |
| Detecção de bugs  | Sim                   | Identifica regression bugs. Evidência: detectou mudança na cor de um botão, mas falhou em rejeitar cores ruins em novos testes por falta de histórico (Baseline). |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | N/A                   | N/A                      |
| Execução de testes automatizados                 | Sim                   | Executa a comparação de estados da tela. Limitação: a IA não identifica contrastes ou combinações de cores que impossibilitam a boa experiência do usuário ao visualizar a tela (disponível apenas no modo Starter). |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Sim                   | Serve como um Quality Gate. Se uma mudança de cor for injetada e houver uma Baseline anterior, o pipeline é alertado. |
| Automação                         | Sim                   | Substitui a revisão visual humana exaustiva por uma comparação algorítmica. |
| Monitoramento                     | N/A                   | N/A                      |
| Documentação técnica automatizada | Sim                   | O Dashboard gera um histórico visual da evolução da interface, servindo como log de mudanças. |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Sim                   | Através da Auto-Maintenance, é possível aceitar uma mudança visual em um teste e propagá-la para todos os outros automaticamente. |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | N/A                   | N/A                      |
| Execução                            | N/A                   | N/A                      |
| Controle                            | Parcial               | Oferece visibilidade sobre a saúde visual do projeto. |
| Encerramento                        | N/A                   | N/A                      |
| Gestão de riscos                    | Parcial               | Mitiga o risco de layouts quebrados, mas o risco de acessibilidade permanece pela falta do relatório de contraste (presente apenas no modo Starter). |
| Estimativas (tempo, custo, esforço) | N/A                   | N/A                      |
| Medição                             | Sim                   | Gera métricas quantitativas de quantos componentes da interface estão em conformidade visual. |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            | Extremamente precisa na comparação de pixels e detecção de mudanças estruturais (regressão), uma vez que a Baseline existe. |
| Profundidade técnica                | ⭐⭐⭐              | Utiliza algoritmos avançados de visão computacional, mas a camada de acessibilidade e contraste entre as cores é ignorada. |
| Contextualização no código/problema | ⭐⭐⭐              | A IA não julga se a interface é boa ou ruim no primeiro envio; ela aceita qualquer entrada como correta. |
| Clareza                             | ⭐⭐⭐⭐⭐            | O Dashboard é visualmente rico e as marcações em rosa neon eliminam qualquer ambiguidade sobre onde está o erro. |
| Aderência às melhores práticas      | ⭐⭐⭐              | Segue os padrões WCAG 2.1, mas exige que o engenheiro ative e verifique manualmente os relatórios de contraste. |
| Consistência entre respostas        | ⭐⭐⭐⭐⭐            | Resultados determinísticos para o mesmo código e mesma Baseline. |
| Ocorrência de alucinações           | Baixa            | Não ocorreram alucinações. |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

* Detecção de regressão estrutural: comparação entre a tela (v1) da baseline e a tela de teste (v2) para identificar elementos removidos (logo) e mundaças de layout
* Desafio de sensibilidade (micro-regressão): Teste de detecção de mudanças quase imperceptíveis, como deslocamento de 1px e alteração de escala de 5% (scale(0.95)).
* Estresse de acessibilidade e contraste: Injeção de combinações de cores ilegíveis (ex: Amarelo no Branco e Verde Limão no Cinza) para avaliar o comportamento da IA frente às normas WCAG.
* Gestão de baselines: Teste de criação de novas referências visuais e como a IA se comporta ao receber uma "verdade" visualmente incorreta.

### ● Resultados quantitativos

* Tempo de execução: média de 8 a 15 segundos para processamento da imagem na nuvem
* Precisão visual: 100% de sucesso na detecção de mudanças em relação à Baseline
* Falsos positivos: 0% usando Match Level Strict

### ● Exemplos (copie trechos de código, respostas etc.)

```js
cy.get('#log-in').invoke('attr', 'style',
'background-color: #ffffcc; color: #ffffff;');

cy.eyesCheckWindow({
    accessibilityRegions: [{
        selector: '#log-in',
        accessibilityType: 'RegularText'
    }]
});
```

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Alta Sensibilidade Configurável: Capacidade de detectar erros milimétricos que passariam despercebidos por revisores humanos.
* Inteligência Visual (Match Levels): Diferente de ferramentas de comparação de pixel simples, ela entende o que é texto, o que é imagem e o que é layout.
* Redução de Código de Teste: Elimina a necessidade de centenas de linhas de should('have.css', ...) ao validar a tela inteira com um único comando.
* Relatório de Acessibilidade Nativo: Fornece auditoria WCAG automática sem necessidade de ferramentas extras como o Axe-Core (apenas para o modo Starter).

### **Limitações**

* Dependência Crítica da Baseline: A IA é "amoral" no primeiro teste; se a primeira versão enviada estiver errada ou feia, ela será aceita como o padrão correto.

---

#  **8. Riscos, Custos e Considerações de Uso**

* Risco de "Falsa Verdade": O maior risco é estabelecer uma Baseline incorreta no início do projeto, o que fará a IA proteger um erro como se fosse um acerto.
* Custos de Licenciamento: Como ferramenta comercial, o custo por "Checkpoint" (imagem enviada) pode ser alto para empresas com milhares de testes diários.
* Dependência de Vendor (Lock-in): Os testes e imagens ficam armazenados na nuvem da Applitools, dificultando a migração para outra ferramenta sem perder o histórico de Baselines.
* Privacidade de Dados: Telas que contêm dados sensíveis de usuários (PII) precisam ser mascaradas antes do envio para a nuvem da ferramenta para conformidade com a LGPD.

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para quais atividades de ES?  
  A Applitools Eyes demonstrou ser excelente para a Garantia de Qualidade (QA) e Manutenção de Software. É ideal para testes de regressão visual em interfaces complexas, portais de e-commerce e dashboards financeiros onde a precisão de cada pixel e a integridade da marca são críticas. É também uma ferramenta poderosa para acelerar o Code Review visual, permitindo que os desenvolvedores vejam exatamente o impacto das suas mudanças no CSS/layout sem precisar de inspeção manual demorada.

* Em quais casos deve ser evitada?  
  Deve ser evitada (ou usada com cautela) em interfaces com conteúdo extremamente dinâmico ou aleatório, como feeds de notícias em tempo real, a menos que sejam configuradas Ignore Regions. Além disso, não deve ser usada como ferramenta de Auditoria de Acessibilidade, uma vez que no modo gratuito os contrastes entre as cores são ignorados.

* Em qual maturidade técnica ela se encontra?  
  A ferramenta encontra-se em um estado de maturidade elevada. Diferente de LLMs generativos que podem alucinar, a IA visual da Applitools é baseada em algoritmos determinísticos de visão computacional. Durante os testes, provou ser estável, integrando-se perfeitamente com o Cypress e oferecendo um dashboard robusto para uso empresarial.

* Vale a pena para a organização?  
  Sim, especialmente para organizações que possuem equipes de Design e Front-end que exigem fidelidade visual absoluta. O custo do licenciamento é compensado pela redução drástica de bugs visuais em produção e pela economia de tempo dos engenheiros. O sucesso da adoção depende de uma cultura de gerenciamento de Baselines.

---

#  **10. Referências e Links Consultados**

* Applitools Documentation – https://applitools.com/docs/
* W3C Web Content Accessibility Guidelines (WCAG) 2.1 – https://www.w3.org/TR/WCAG21/
* Cypress.io Documentation – https://docs.cypress.io/
