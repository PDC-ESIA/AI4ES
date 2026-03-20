# **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                 |
|---------------------------------|---------------------------------------------------------------------------|
| **Nome da ferramenta**          | ReqView                                                                   |
| **Fabricante / Comunidade**     | Eccam                                                                     |
| **Site oficial / documentação** | https://www.reqview.com                                                  |
| **Tipo de ferramenta**          | Ferramenta de gerenciamento de requisitos (Requirements Management Tool) |
| **Licença / acesso**            | Comercial, com plano gratuito limitado                                    |

---

# **2. Informações do Modelo de IA Utilizado**

>  Observação importante: o ReqView **não declara oficialmente o uso de um modelo de IA generativa (LLM)** integrado de forma nativa (como GPT, Claude ou similares). O uso de IA ocorre apenas de forma **indireta**, via técnicas de NLP em serviços customizados ou estudos de caso.

| Item                              | Descrição                                                                 |
|----------------------------------|---------------------------------------------------------------------------|
| **Tipo de IA Generativa**         | NLP tradicional / análise semântica (não generativa)                      |
| **Nome do Modelo**                | N/A                                                                       |
| **Versão**                        | N/A                                                                       |
| **Tamanho (nº de parâmetros)**    | N/A                                                                       |
| **Acesso**                        | N/A                                                                       |
| **Suporte a Fine-tuning**         | N/A                                                                       |
| **Suporte a RAG**                 | N/A                                                                       |
| **Métodos de prompting suportados** | N/A                                                                     |
| **Ferramentas adicionais**        | Serviços customizados de NLP, integrações externas                        |

---

# **3. Contexto de Execução**

| Item                               | Descrição                                                                 |
|------------------------------------|---------------------------------------------------------------------------|
| **Onde roda?**                     | Local (desktop) e Cloud (colaboração)                                     |
| **Infraestrutura utilizada no teste** | N/A                                                                    |
| **Custos (quando aplicável)**      | Plano gratuito limitado e licenças pagas (até Enterprise)                 |

---

# **4. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo:
- O que a ferramenta faz
- Como faz
- Exemplos / evidências
- Limitações observadas

Use N/A quando não aplicável.

---

## **4.1. Requisitos de Software**

| Subatividade              | Suporte da Ferramenta | Evidências / Observações |
|---------------------------|-----------------------|--------------------------|
| Elicitação                | Parcial               | Importação de documentos e requisitos textuais |
| Análise                   | Sim                   | Análise de impacto e rastreabilidade |
| Priorização               | N/A                   | Não há priorização automática baseada em IA |
| Modelagem                 | N/A                   | Não suporta UML/SysML |
| Validação / Verificação   | Sim                   | Verificação de cobertura de requisitos |
| Documentação              | Sim                   | Exportação para PDF, Word, HTML |

---

## **4.2. Arquitetura de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
|----------------------------------|-----------------------|--------------------------|
| Geração de designs arquiteturais | N/A                   | Não suportado |
| Decisões arquiteturais           | N/A                   | Sem apoio por IA |
| Avaliação de trade-offs          | Parcial               | Análise de impacto entre requisitos |
| Uso de padrões arquiteturais     | N/A                   | Não aplicável |

---

## **4.3. Design de Software**

| Subatividade                         | Suporte da Ferramenta | Evidências / Observações |
|-------------------------------------|-----------------------|--------------------------|
| Sugestão/uso de padrões de projeto  | N/A                   | Não aplicável |

---

## **4.4. Construção de Software**

| Subatividade       | Suporte da Ferramenta | Evidências / Observações |
|--------------------|-----------------------|--------------------------|
| Geração de código  | N/A                   | ReqView não gera código |
| Refatoração        | N/A                   | Não aplicável |
| Detecção de bugs   | N/A                   | Não aplicável |

---

## **4.5. Teste de Software**

| Subatividade                                      | Suporte da Ferramenta | Evidências / Observações |
|--------------------------------------------------|-----------------------|--------------------------|
| Geração de testes (unit., integração, aceitação) | N/A                   | Não aplicável |
| Execução de testes automatizados                 | N/A                   | Não aplicável |

---

## **4.6. Operações de Software**

| Subatividade                            | Suporte da Ferramenta | Evidências / Observações |
|----------------------------------------|-----------------------|--------------------------|
| CI/CD                                  | N/A                   | Não aplicável |
| Automação                              | Parcial               | Integração com Git/SVN |
| Monitoramento                          | N/A                   | Não aplicável |
| Documentação técnica automatizada      | Sim                   | Relatórios e exportações |

---

## **4.7. Manutenção de Software**

| Subatividade             | Suporte da Ferramenta | Evidências / Observações |
|--------------------------|-----------------------|--------------------------|
| Correções automatizadas  | N/A                   | Não aplicável |

---

## **4.8. Gerenciamento de Projeto de Software**

| Subatividade                          | Suporte da Ferramenta | Evidências / Observações |
|--------------------------------------|-----------------------|--------------------------|
| Planejamento                         | Parcial               | Organização por requisitos |
| Execução                             | Sim                   | Fluxos versionados |
| Controle                             | Sim                   | Versionamento e histórico |
| Encerramento                         | N/A                   | Não aplicável |
| Gestão de riscos                     | Sim                   | Rastreabilidade de riscos |
| Estimativas (tempo, custo, esforço)  | N/A                   | Sem suporte por IA |
| Medição                              | Parcial               | Métricas internas |

---

# **5. Qualidade das Respostas**

| Critério                             | Avaliação       | Observações |
|-------------------------------------|-----------------|-------------|
| Precisão                             | ⭐⭐⭐⭐⭐           | Baseado em documentação oficial |
| Profundidade técnica                 | ⭐⭐⭐⭐            | IA não é foco principal |
| Contextualização no código/problema  | ⭐⭐⭐⭐            | Adequado para requisitos |
| Clareza                              | ⭐⭐⭐⭐⭐           | Interface e docs claras |
| Aderência às melhores práticas       | ⭐⭐⭐⭐            | Segue padrões de engenharia |
| Consistência entre respostas         | ⭐⭐⭐⭐            | Alta |
| Ocorrência de alucinações            | Baixa           | Informações verificáveis |

---

# **6. Experimentos Realizados**

### Descrição das tarefas testadas
N/A – Não foram realizados testes com IA generativa, pois a ferramenta não possui IA nativa pública.

---

# **7. Pontos Fortes e Fracos da Ferramenta**

### Pontos fortes
- Forte rastreabilidade de requisitos  
- Boa integração com versionamento  
- Documentação estruturada e exportável  

### Limitações
- Não possui IA generativa integrada  
- Não gera requisitos automaticamente  
- Sem apoio direto a decisões arquiteturais por IA  

---

# **8. Riscos, Custos e Considerações de Uso**

- Dependência de ferramenta proprietária  
- Custos elevados em planos enterprise  
- Necessidade de IA externa para automação avançada  
- Limitações para NLP avançado e RAG  

---

# **9. Conclusão Geral da Análise**

- Adequada para engenharia de requisitos formal e rastreabilidade  
- Deve ser evitada quando se busca automação baseada em LLM  
- Ferramenta madura no domínio tradicional de requisitos  
- Vale a pena para organizações que priorizam compliance e documentação  

---

# **10. Referências e Links Consultados**

- https://www.reqview.com  
- https://www.reqview.com/cases/similarity  
- https://www.reqview.com/custom-services  
- https://www.g2.com/products/reqview  

