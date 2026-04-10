# 📘 **PDC – IA Generativa Aplicada à Engenharia de Software**

**Centro de Excelência em IA (CEIA/UFG)**
**Programa de Desenvolvimento de Competências – 2025–2026**

---

## 📌 **Visão Geral do Projeto**

Este repositório centraliza toda a documentação, código, artefatos, experimentos e relatórios produzidos no âmbito do projeto **“IA Generativa Aplicada à Engenharia de Software”**, conduzido pelo **PDC (Programa de Desenvolvimento de Competências)** do **CEIA/UFG**.

O projeto investiga, de forma sistemática e aplicada, o uso de IA Generativa (LLMs, modelos multimodais e agentes inteligentes) nas atividades definidas pelo **SWEBOK**, com foco em:

* Aceleração da prototipação
* Automação inteligente de etapas do SDLC
* Benchmarking de assistentes de código
* Pesquisa aplicada em IA4SE
* Implementação de pipeline LLMOps
* Desenvolvimento de agentes especializados
* Estudo de caso aplicado: **TACO – Teacher Assistant for Coding Online**

---

## 🎯 **Objetivos do Projeto**

1. **Avaliar comparativamente assistentes de código comerciais e plataformas low-code**, identificando pontos fortes, limitações e casos de uso ideais.
2. **Benchmarking estruturado de LLMs open-source** para tarefas de Engenharia de Software.
3. **Criar um pipeline completo de LLMOps** com versionamento, experiment tracking e CI/CD para modelos.
4. **Desenvolver protótipos de IA** para requisitos, testes, refatoração e detecção de bugs.
5. **Integrar LLMs à plataforma TACO**, validando a capacidade de agentes inteligentes especializados.

---

## 🧩 **Estrutura do Repositório**

```
/
├── adk/                        # Aplicação de agentes (Google ADK)
│   ├── app/
│   │   └── main.py             # Entry point FastAPI + ADK
│   ├── runners/                # Apps ADK expostos (discovery dir)
│   │   └── orchestrator/       # Único ponto de entrada
│   ├── agents/
│   │   ├── roles/              # Agentes especialistas (coder, reviewer, …)
│   │   └── workflows/          # Composições (SequentialAgent, …)
│   ├── shared/
│   │   └── tools/              # Ferramentas reutilizáveis (git, filesystem)
│   └── tests/
│
├── docs/
│   ├── squad1/
│   │   ├── revisao-sistematica/
│   │   ├── comparativo-ferramentas/
│   │   └── templates/
│   ├── squad2/
│   │   ├── ambiente/
│   │   ├── experimentos/
│   │   └── kit-benchmarking/
│   ├── squad3/
│   │   └── taco/
│   └── gestao/
│       ├── atas/
│       ├── cronograma/
│       └── padroes-documentacao.md
│
├── src/
│   ├── prototipos/
│   ├── notebooks/
│   └── pipelines/
│
├── benchmarks/
│   ├── tarefas/
│   ├── resultados/
│   └── scripts/
│
├── .github/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── README.md
├── CONTRIBUTING.md
├── GUIDE_GITFLOW.md
└── LICENSE
```

---

## 🧑‍🔬 **Squads e Responsabilidades**

### 🔷 **Squad 1 – Revisão Sistemática + Análise Comparativa**

* Condução da **Revisão Sistemática da Literatura (RSL)**
* Avaliação comparativa de assistentes de código
* Geração de relatórios e do **artigo científico**
* Alimentar os artefatos conceituais para construção dos agentes

📄 Protocolos:

* Protocolo de RSL
* Protocolo de Avaliação Comparativa
* Templates de análise individual

---

### 🔶 **Squad 2 – Ambiente + Experimentação**

* Configuração de ambientes de desenvolvimento
* Execução de experimentos com/sem IA
* Implementação do **Kit de Benchmarking**
* Coleta de métricas: tempo, erros, LOC, cobertura, legibilidade
* Consolidação dos dados para análise integrada

📄 Artefatos:

* Tarefas padronizadas
* Scripts de coleta e medição
* Relatórios de experimentação

---

### 🔷 **Squad 3 – TACO + Integração GenAI**

* Estudo da plataforma TACO
* Mapeamento de pontos de integração
* Prototipação do agente LLM + TACO
* Suporte à arquitetura multiagentes

📄 Artefatos:

* Documento de visão de integração
* Protótipo TRL-4

---

### 🟩 **Gestão**

* Coordenação geral
* Gestão de cronograma, entregas e documentação
* Manutenção da estrutura do repositório
* Supervisão das squads e integração dos resultados

---

## 🛠️ **Como Contribuir**

Leia o [CONTRIBUTING.md](./CONTRIBUTING.md) para as regras completas e o [GUIDE_GITFLOW.md](./GUIDE_GITFLOW.md) para um guia rápido. Em resumo:

### 📌 Fluxo de contribuições

1. Crie uma branch a partir de `develop` seguindo o padrão `feature/<equipe>/<issue>-descricao`
2. Faça commits usando **Conventional Commits**: `tipo(escopo): descrição #issue`
3. Sincronize com `develop` e resolva conflitos localmente
4. Abra um Pull Request usando o [template padrão](./.github/PULL_REQUEST_TEMPLATE.md)
5. Aguarde as aprovações e status checks antes do merge

### 🏷️ Sub-equipes e prefixos

| Sub-equipe  | Prefixo (branch/scope) | Foco                                 |
| ----------- | ---------------------- | ------------------------------------ |
| Requisitos  | `req`                  | Levantamento e análise de requisitos |
| Design      | `design`               | Arquitetura e decisões técnicas      |
| Codificação | `code`                 | Implementação e refatoração          |
| Testes      | `test`                 | Planos e execução de testes          |

---
