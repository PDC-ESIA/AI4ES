# **Matriz de Conformidade e Rastreabilidade \- Macroentrega 1 (ME1)**

**Projeto:** Capacitação em IA Generativa para Engenharia de Software (AI4SE)  
**Responsável:** Squad 2 \- Frente 3 (LLMs e Configuração de Ambiente)  
**Data:** 09/12/2025  
---

## **1\. Análise dos Objetivos Específicos (OE)**

Mapeamento entre o objetivo do edital e a entrega técnica realizada.

| Objetivo Específico (Projeto) | Status | Evidência de Entrega (O que fizemos?) | Gaps / Pendências (O que falta?) |
| ----- | :---: | :---: | :---: |
| **OE1:** Avaliação comparativa de assistentes de código comerciais (ex: Copilot, CodeWhisperer). | Parcial | Avaliamos os **modelos base** (Claude, GPT-5) que alimentam essas ferramentas. | Falta testar os **plugins/ferramentas** (UX/IDE) na prática. |
| **OE2:** Benchmarking de desempenho de LLMs open-source (CodeLlama, DeepSeek). | Parcial | Selecionamos **DeepSeek V2**, **Llama 3.1**, **GAIA (GEMMA)** Justificativa baseada em arquitetura MoE vs Denso. | Execução dos scripts de teste (aguardando servidor). |
| **OE5:** Prototipar integração explorando arquiteturas API vs. Modelos Locais. | Completo | Definimos a **Arquitetura Híbrida**: API para validação (Claude) e Local para privacidade (Llama). | Implementação do script de integração (Motor de Inferência). |

## **2\. Análise dos Resultados Esperados**

Verificação dos entregáveis tangíveis prometidos para a ME1.

| Resultado Esperado | Entregue? | Localização / Detalhe |
| :---: | :---: | :---: |
| **Relatório com benchmarking de ferramentas de LLMs** | Em Andamento | *Relatório V2 (Seções 3, 4 e 5\)*: Cobre a análise teórica e seleção de modelos. |
| **Ambiente de desenvolvimento e experimentação** | Em Andamento | Definimos o **Sizing de Hardware** (Tabela de VRAM) e a **Stack de Software** (Docker, Python 3.10).  Falta o deploy físico. |
| **Acesso a recursos de nuvem e repositórios** | Sim | Mapeamos os custos de API (Nuvem) e os links dos repositórios Hugging Face (Local). |

## **3\. Auditoria do Plano de Atividades (ME1)**

Status das tarefas operacionais dos Meses 1-4.

| Atividade | Prazo | Status Real | Justificativa / Ação Corretiva |
| :---: | :---: | :---: | :---: |
| **1.2 Configuração do Ambiente** | M1-M3 | Bloqueado | Requisitos de Hardware definidos. **Bloqueio:** Aguardando a chegada física do servidor. |
| **1.3 Avaliação Sistemática** | M2-M4 | Iniciado | Modelos selecionados. Scripts de teste sendo desenhados. Execução pendente de infra. Pendência de recursos financeiros e computacionais. |

## **4\. Parecer Final da Frente 3**

Resumo da Situação:  
A Frente 3 concluiu com partes a etapa de Planejamento e Engenharia. Entregamos a fundamentação necessária para evitar erros de aquisição (ex: inviabilidade do DeepSeek local).  
**Próximos Passos Prioritários:**

1. Escrever o script "Motor de Inferência" para consumir o JSON da Frente 2\.  
2. Configurar o Docker com isolamento de rede (--network none) assim que o servidor for liberado.  
3. Expandir a análise para incluir a experiência de uso (DX) dos plugins comerciais (OE1).