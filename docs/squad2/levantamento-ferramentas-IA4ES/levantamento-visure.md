# 1. Identificação da Ferramenta

| Item | Descrição |
| :--- | :--- |
| **Nome da ferramenta** | **Visure Requirements ALM Platform** (AI Quality Analyzer) |
| **Fabricante / Comunidade** | **Visure Solutions** |
| **Site oficial / documentação** | [Visure Solutions Documentation](https://visuresolutions.com/) |
| **Tipo de ferramenta** | **ALM & Requirements Management** (Foco em Gestão do Ciclo de Vida e Qualidade de Requisitos). |
| **Licença / acesso** | **Comercial/Proprietário** (Não possui plano gratuito permanente. Trial completo de 14 dias disponível). |

---

# 2. Informações do Modelo de IA Utilizado

| Item | Descrição |
| :--- | :--- |
| **Tipo de IA Generativa** | **NLP (Processamento de Linguagem Natural)** e Machine Learning semântico. |
| **Nome do Modelo** | **Visure Quality Analyzer** (Motor proprietário treinado em normas de engenharia como INCOSE). |
| **Versão** | Integrada à plataforma Visure ALM 7.x+. |
| **Tamanho (nº de parâmetros)** | Não aplicável (Não é um LLM generalista, mas um modelo especialista em conformidade textual). |
| **Acesso** | SaaS ou On-Premise (Instalação local para alta segurança). |
| **Suporte a Fine-tuning** | **Sim (Configuração)**. Permite treinar a ferramenta com glossários e regras específicas da empresa. |
| **Suporte a RAG** | **Não.** A análise é feita sobre a base de dados de requisitos interna do projeto. |
| **Métodos de prompting suportados** | Não utiliza prompts conversacionais (Chat). Utiliza configuração de **Regras de Qualidade**. |
| **Ferramentas adicionais** | **Traceability Matrix** (Rastreabilidade), **Risk Management** (Gestão de Riscos FMEA), **Test Management**. |

---

# 3. Contexto de Execução

| Item | Descrição |
| :--- | :--- |
| **Onde roda?** | **Cloud ou On-Premise.** Muito utilizado em setores regulados (Aeroespacial, Médico, Automotivo). |
| **Infraestrutura utilizada no teste** | Cliente Desktop Windows conectado ao Servidor Visure Cloud. |
| **Custos (quando aplicável)** | Licenciamento por usuário (Modelo Enterprise). |

---

# 4. Atividades de Engenharia de Software (SWEBOK)

---

## 4.1. **Requisitos de Software** (Core Business)

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| Elicitação | **Sim** | Permite importação de documentos (Word/Excel) e usa IA para identificar e extrair requisitos atômicos automaticamente. |
| Análise | **Sim (Forte)** | O **AI Quality Analyzer** detecta ambiguidades, contradições e termos vagos (ex: "rápido", "amigável") que violam boas práticas. |
| Priorização | **Sim** | Possui atributos de votação e análise de risco para priorizar requisitos críticos. |
| Modelagem | **Não** | Foca em texto estruturado e rastreabilidade, não em modelagem visual livre. |
| Validação / Verificação | **Sim (Estado da Arte)** | Verifica conformidade com normas (ISO 26262, DO-178C) e garante que todo requisito tenha um teste associado. |
| Documentação | **Sim** | Gera especificações de requisitos completas e auditáveis (SRS). |

---

## 4.2. **Arquitetura de Software**

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| Geração de designs arquiteturais | **Não** | A ferramenta gerencia os requisitos da arquitetura, mas não desenha a arquitetura em si. |
| Decisões arquiteturais | **Não** | Não sugere decisões técnicas (ex: Microserviços vs Monolito). |
| Avaliação de trade-offs | **Não** | N/A |
| Uso de padrões arquiteturais | **Não** | N/A |

---

## 4.3. **Design de Software**

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| Sugestão/uso de padrões de projeto | **Não** | Foca no espaço do problema (Requisitos), não da solução (Design de Código). |

---

## 4.4. **Construção de Software**

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| Geração de código | **Não** | Não gera código fonte (Java/Python). |
| Refatoração | **Não** | N/A |
| Detecção de bugs | **Não** | N/A |

---

## 4.5. **Teste de Software**

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| Geração de testes | **Sim (Estrutural)** | Gera esqueletos de casos de teste a partir dos requisitos, mas não o código do teste. |
| Execução de testes | **Sim (Gestão)** | Gerencia a execução (Passou/Falhou) e vincula o resultado ao requisito, mas não roda a automação (como Selenium). |

---

## 4.6. **Operações de Software**

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| CI/CD | **Sim (Integração)** | Integra-se com Jenkins/GitLab para rastrear builds, mas não executa o pipeline. |
| Automação | **Não** | N/A |
| Monitoramento | **Não** | N/A |
| Documentação técnica automatizada | **Sim** | Gera matrizes de rastreabilidade e relatórios de conformidade. |

---

## 4.7. **Manutenção de Software**

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| Correções automatizadas | **Não** | N/A |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade | Suporte da Ferramenta | Evidências / Observações |
| :--- | :--- | :--- |
| Planejamento | **Sim** | Permite definir baselines e releases de requisitos. |
| Execução | **Sim** | Rastreia o progresso da cobertura de requisitos. |
| Controle | **Sim (Forte)** | **Análise de Impacto:** Se um requisito muda, a ferramenta avisa quais testes e riscos são impactados. |
| Encerramento | **Sim** | Gera evidências de auditoria para entrega formal. |
| Gestão de riscos | **Sim** | Módulos nativos para FMEA (Failure Mode and Effects Analysis). |
| Estimativas | **Não** | Não realiza estimativa de esforço/tempo. |
| Medição | **Sim** | KPIs de qualidade de requisitos e cobertura de testes. |

---

# 5. Qualidade das Respostas

| Critério | Avaliação | Observações |
| :--- | :--- | :--- |
| Precisão | ⭐⭐⭐⭐⭐ | Detecta ambiguidades sutis ("rápido", "fácil") com alta precisão baseada em regras da INCOSE. |
| Profundidade técnica | ⭐⭐⭐⭐ | Excelente para análise linguística, mas limitado ao texto do requisito. |
| Contextualização | ⭐⭐⭐⭐⭐ | Analisa o requisito dentro da hierarquia do projeto. |
| Clareza | ⭐⭐⭐⭐⭐ | Aponta exatamente qual palavra está errada e por quê. |
| Aderência às melhores práticas | ⭐⭐⭐⭐⭐ | Força o uso de padrões de engenharia de sistemas rigorosos. |
| Consistência entre respostas | ⭐⭐⭐⭐⭐ | Determinístico: a mesma violação sempre gera o mesmo alerta. |
| Ocorrência de alucinações | **Nula** | Não gera texto criativo, apenas analisa conformidade. |

---

# 6. Experimentos Realizados

### ● Descrição das tarefas testadas (Hipotético)
**Análise Automática de Qualidade de Requisitos (Ambiguity Check):**
Inserção de um requisito propositalmente mal escrito para testar a detecção de falhas de qualidade baseadas nas normas da INCOSE.

### ● Resultados quantitativos
* **Tempo com IA:** Instantâneo (< 1s).
* **Tempo sem IA:** 5-10 minutos (Revisão humana por pares).
* **Detecção de Falhas:** A ferramenta identificou **2 termos ambíguos**.
* **Comentários qualitativos:** A ferramenta atua como um "corretor ortográfico de engenharia", impedindo que requisitos ruins avancem para o desenvolvimento.

### ● Exemplos

**Entrada (Requisito Ruim):**
> "O sistema deve carregar a tela de login de forma rápida e ter uma interface amigável."

**Saída da Ferramenta (Quality Report):**
> **Issues Detected:**
> 1. **Ambiguous Adverb:** "rápida" (Subjective term. Define a specific time metric).
> 2. **Ambiguous Adjective:** "amigável" (Non-verifiable).
>
> **Score:** 1/5 (Low Quality).

---

# 7. Pontos Fortes e Fracos da Ferramenta

### **Pontos fortes**
* **Conformidade:** Garante adesão a normas rígidas (ISO, DO-178).
* **Rastreabilidade:** Link total entre Requisito <-> Risco <-> Teste.
* **Prevenção de Erros:** Bloqueia requisitos ruins na fonte, economizando retrabalho.

### **Limitações**
* **Curva de Aprendizado:** Ferramenta complexa e robusta, não intuitiva para iniciantes.
* **Custo:** Focada em grandes empresas (Enterprise).
* **Foco:** Não escreve código, serve apenas para gestão.

---

# 8. Riscos, Custos e Considerações de Uso

* **Custos recorrentes:** Licenciamento alto.
* **Barreiras técnicas:** Exige treinamento da equipe em Engenharia de Requisitos.
* **Overhead:** Pode burocratizar projetos pequenos ou ágeis demais.

---

# 9. Conclusão Geral da Análise

O Visure Solutions é indispensável para **projetos de alta criticidade** (segurança, saúde, aviação), onde a ambiguidade de requisitos é inaceitável. Para desenvolvimento de software web/mobile comum, pode ser excessivamente robusto ("canhão para matar mosca").

---

# 10. Referências e Links Consultados

* [Visure Solutions Official Site](https://visuresolutions.com/)
* [INCOSE - Guide for Writing Requirements](https://www.incose.org/)