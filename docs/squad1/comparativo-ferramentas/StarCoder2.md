#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |  StarCoder2                                                                    |
| **Fabricante / Comunidade**     |  BigCode Project (Hugging Face + ServiceNow Research + colaboração comunitária)|
| **Site oficial / documentação** |  https://github.com/bigcode-project/starcoder2                                 |
| **Tipo de ferramenta**          |  Modelo LLM especializado em código (Code LLM)                                 |
| **Licença / acesso**            |  OpenRAIL (open-source com restrições de uso responsáveis)                     |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM especializado em código                                  |
| **Nome do Modelo**                  | StarCoder2 (com variantes 3B, 7B, 15B)                       |
| **Versão**                          | 2 (StarCoder 2)                                              |
| **Tamanho (nº de parâmetros)**      | 3 bilhões, 7 bilhões e 15 bilhões de parâmetros              |
| **Acesso**                          | Open-weight, executável localmente ou em servidores          |
| **Suporte a Fine-tuning**           | Sim: LoRA e full fine-tuning                                 |
| **Suporte a RAG**                   | Sim                                                          |
| **Métodos de prompting suportados** | Fill-in-the-Middle (FIM), prompting padrão, CoT e variantes dependentes do pipeline|
| **Ferramentas adicionais**          | Integração com Hugging Face e com o VSCode (extensões)       |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Local ou Cloud (GPU recomendada)        |
| **Infraestrutura utilizada no teste** | GPUs de larga escala; treinamento em até 4.3 trilhões de tokens|
| **Custos (quando aplicável)**         | Gratuito (open-weight), custo apenas de infraestrutura para rodar|

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              | Parcial               |Modelo entende linguagem natural e pode ajudar a converter requisitos em descrições estruturadas|
| Análise                 | Parcial               |Tem a capacidade de discutir requisitos, mas não é seu foco principal|
| Priorização             | N/A                   |Não encontrei evidências nas fontes que tive acesso|
| Modelagem               | Parcial               |Pode gerar artefatos textuais, mas não modelagem formal|
| Validação / Verificação | Parcial               |Pode verificar a consistência textual dos requisitos|
| Documentação            | Sim                   |Tem um bom suporte a documentação técnica, incluindo markdown e explicações|

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |Parcial                |Sugere arquiteturas comuns com base em padrões conhecidos|
| Decisões arquiteturais           |Parcial                |Explica vantagens e desvantagens usando conhecimento derivado do corpus técnico|
| Avaliação de trade-offs          |Parcial                |Consegue comparar alternativas|
| Uso de padrões arquiteturais     |Parcial                |Reconhece padrões populares, mas não substitui análise arquitetural completa|

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Sim                   | O corpus inclui vasta documentação, issues, PRs e notebooks, o que aumenta a capacidade do modelo em padrões práticos|

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Sim                   | É o ponto forte da linguágem: treinamento em 619 linguagens + PRs + notebooks|
| Refatoração       | Sim                   | O corpus inclui milhões de pull requests, favorecendo aprendizagem de refatoração|
| Detecção de bugs  | Sim                   | Bom desempenho em benchmarks de raciocínio sobre código e detecção de falhas|

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Sim                   |Produz testes unitários e casos de validação coerentes|
| Execução de testes automatizados                 | N/A                   |                          |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Parcial               | Cria pipelines com estruturações válidas|
| Automação                         | Sim                   | Gera scripts Bash, Python e YAML de automação|
| Monitoramento                     | N/A                   |                          |
| Documentação técnica automatizada | Sim                   |Gera documentação clara para implantação, APIs e integrações|

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Sim                   | Modelo treinado em PRs, revisões e diffs (ótimo para correções)|

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Parcial               | Gera cronogramas e estimativas textuais gerais|
| Execução                            | N/A                   |                          |
| Controle                            | N/A                   |                          |
| Encerramento                        | N/A                   |                          |
| Gestão de riscos                    | Parcial               | Consegue avaliar riscos recorrentes em projetos de software|
| Estimativas (tempo, custo, esforço) | Parcial               | Produz estimativas qualitativas; não possui métricas profissionais integradas|
| Medição                             | N/A                   |                          |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            |Valida por benchmarks consistentemente entre os melhores modelos open-source|
| Profundidade técnica                | ⭐⭐⭐⭐⭐            |Treinado em PRs reais, documentação e código fonte e diffs|
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            |Janela de contexto efetiva de 16k tokens ajuda a manter coerência em arquivos longos|
| Clareza                             | ⭐⭐⭐⭐⭐            |Produz texto direto e explicativo|
| Aderência às melhores práticas      | ⭐⭐⭐⭐⭐            |Influenciada pelo dataset de PRs e código real de alta qualidade|
| Consistência entre respostas        | ⭐⭐⭐⭐               |Alta com pequena variação dependendo da linguagem pedida|
| Ocorrência de alucinações           | Baixa                    |Um dos modelos de código open-source com menor alucinação|

---

#  **6. Experimentos Realizados**
Não foram realizados experimentos.
---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Pelas métricas pode ser considerado um dos melhores modelos open-source (Open-weight) da atualidade;
* Excelência em geração, refatoração e entendimento de código;
* Compatível com mais de 619 linguagens;
* Dataset transparente, auditável e massivo (>4T tokens).
* Ótima performance com recursos abertos.
* Suporte ao FIM e janela de contexto longa.
* Execução local possível nas versões menores.
* Variantes de “heads” permitem geração, classificação e análise de tokens.

### **Limitações**

* Não possui capacidades multimodais;
* Qualidade inferior a modelos proprietários muito maiores como por exemplo o GPT-4.1;
* A inferência local pode ser pesada para o modelo 15B.

---

#  **8. Riscos, Custos e Considerações de Uso**

* Possui custos de infraestrutura se rodado localmente;
* Como é open-source, não há garantia de suporte;
* Mesmo que os riscos de alucinação do modelos sejam menores, elas ainda são presentes;
* A privacidade depende da infraestrutura onde ele é executado (local vs. nuvem);
* Possui a necessidade de hardware potente (especialmente o modelo 15B).

---

#  **9. Conclusão Geral da Análise**

O StarCoder2 é uma das opções mais maduras, práticas e transparentes para desenvolvimento assistido por IA em ambientes open-source. Ele é especialmente eficaz em:
* geração de código;
* Refatoração;
* Criação de testes;
* Documentação técnica;
* Manutenção e correções.

Deve ser evitado em cenários que exigem:
* Multimodalidade;
* Contextos muito maiores que 16k;
* Integrações operacionais profundas sem supervisão humana.

A sua maturidade técnica é alta
Seu Custo-benefício é excelente por ser open-weight e altamente performático.

---

#  **10. Referências e Links Consultados**
* https://github.com/bigcode-project/starcoder2
* Artigo: StarCoder 2 and The Stack v2: The Next Generation, presente em: https://arxiv.org/pdf/2402.19173