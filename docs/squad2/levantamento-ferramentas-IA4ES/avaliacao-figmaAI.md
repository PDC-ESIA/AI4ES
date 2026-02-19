#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |      Figma AI                                                                          |
| **Fabricante / Comunidade**     |        Figma Inc.                                                                        |
| **Site oficial / documentação** |        https://www.figma.com/ai/                                                                        |
| **Tipo de ferramenta**          | Plataforma de design colaborativo com IA generativa integrada (UX/UI e Arquitetura) |
| **Licença / acesso**            | Comercial                                             |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM multimodal (texto, layout e imagens)                        |
| **Nome do Modelo**                  | Utiliza modelos de terceiros (como OpenAI GPT-4o) integrados a modelos próprios |
| **Versão**                          | Não divulgada                                                             |
| **Tamanho (nº de parâmetros)**      | Não divulgado                                                |
| **Acesso**                          | Cloud / Local                          |
| **Suporte a Fine-tuning**           | Não                     |
| **Suporte a RAG**                   | Parcial (contexto do próprio arquivo)                                                      |
| **Métodos de prompting suportados** | Natural Language Prompting (Text-to-Design)                            |
| **Ferramentas adicionais**          | Figma Design, FigJam, Dev Mode    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Cloud (Navegador ou Desktop App)                 |
| **Infraestrutura utilizada no teste** | Gerenciada pelo Figma (AWS/Azure)   |
| **Custos (quando aplicável)**         | Plano Anual, cobrança mensal Profissional: U$3, U$12, U$16; Organização: U$5, U$25, U$55; Enterprise: U$5, U$35, U$90. |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo, descreva:

* **O que a ferramenta faz** Ajuda na elicitação visual e prototipagem rápida de requisitos.
* **Como faz** Através do "First Draft", transforma descrições de texto em telas funcionais.
* **Exemplos / evidências** Gerar um formulário de login ou dashboard financeiro a partir de um comando de voz/texto.
* **Limitações observadas** Não substitui a análise de regras de negócio complexas; foca na camada visual.


---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |    Parcial                   | Geração de telas a partir de prompts                         |
| Análise                 |   Parcial                    | Exploração visual de soluções                         |
| Priorização             |   N/A                    |    Não suportado                      |
| Modelagem               |   Sim                    |      Criação automática de layouts                    |
| Validação / Verificação |    Parcial                   |  Protótipos interativos                       |
| Documentação            |    Parcial                   |  Comentários no design                        |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais |     Parcial                  |  Estrutura de navegação                        |
| Decisões arquiteturais           |     N/A                  |     Fora do escopo                     |
| Avaliação de trade-offs          |     N/A                  |    Não aplicável                      |
| Uso de padrões arquiteturais     |    Parcial                   |   Padrões de UI/UX                       |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto |     Parcial                  |   Componentes reutilizáveis                       |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código |      Parcial                 |    Exportação via Dev Mode                      |
| Refatoração       |     N/A                  |    Não aplicável                      |
| Detecção de bugs  |    N/A                   |   Não aplicável                       |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |      N/A                 |   Não suportado                       |
| Execução de testes automatizados                 |       N/A                |   Não suportado                      |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |      N/A                 |    Fora do escopo                      |
| Automação                         |     Parcial                  |   Automação de design                       |
| Monitoramento                     |     N/A                  |      Não aplicável                    |
| Documentação técnica automatizada |     Parcial                  |  Especificações visuais                        |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |      Parcial                 |     Ajustes automáticos de layout                     |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        |    Parcial                   |   Quadros e fluxos                       |
| Execução                            |    Parcial                   |    Colaboração em tempo real                      |
| Controle                            |    Parcial                   |   Histórico de versões                       |
| Encerramento                        |   N/A                    |   Não suportado                      |
| Gestão de riscos                    |  N/A                     |   Não aplicável                       |
| Estimativas (tempo, custo, esforço) |   N/A                    |   Não aplicável                       |
| Medição                             |   N/A                    |  Não aplicável                        |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐            |  Boa para UI/UX           |
| Profundidade técnica                | ⭐⭐⭐           |   Limitada a design          |
| Contextualização no código/problema | ⭐⭐⭐⭐            |   Usa contexto do arquivo          |
| Clareza                             | ⭐⭐⭐⭐            |  Interfaces claras           |
| Aderência às melhores práticas      | ⭐⭐⭐⭐            |  Padrões de design           |
| Consistência entre respostas        | ⭐⭐⭐⭐            |    Resultados estáveis         |
| Ocorrência de alucinações           | Baixa |             |

---

#  **6. Experimentos Realizados**

### ● Geração automática de telas de interface a partir de prompts em linguagem natural.

### ● Criação de protótipo de alta fidelidade para um sistema web fictício.

### ● Ajustes automáticos de layout e tipografia sugeridos pela IA.

### ● Uso do Dev Mode para inspeção de estilos e exportação de trechos de código CSS.


## Resultados quantitativos
### Usando IA
* Tempo: 40 minutos.
* Número de erros: 5.
* Qualidade do código: Alta.
* Cobertura de testes: Alta. 
* Documentação: Completa.

### Sem uso de IA
* Tempo: 5 horas.
* Número de erros: Inúmeros.
* Qualidade do código: Variável.
* Cobertura de testes: Baixa. 
* Documentação: Totalmente ignorada no rascunho.

### ● Exemplos (copie trechos de código, respostas etc.)
### Usando IA
Trecho de Código CSS: 
@custom-variant dark (&:is(.dark *));

:root {
  --font-size: 16px;
  --background: #ffffff;
  --foreground: oklch(0.145 0 0);
  --card: #ffffff;
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: #030213;
  --primary-foreground: oklch(1 0 0);
  --secondary: oklch(0.95 0.0058 264.53);
  --secondary-foreground: #030213;
  --muted: #ececf0;
  --muted-foreground: #717182;
  --accent: #e9ebef;
  --accent-foreground: #030213;
  --destructive: #d4183d;
  --destructive-foreground: #ffffff;
  --border: rgba(0, 0, 0, 0.1);
  --input: transparent;
  --input-background: #f3f3f5;
  --switch-background: #cbced4;
  --font-weight-medium: 500;
  --font-weight-normal: 400;
  --ring: oklch(0.708 0 0);
  --chart-1: oklch(0.646 0.222 41.116);
  --chart-2: oklch(0.6 0.118 184.704);
  --chart-3: oklch(0.398 0.07 227.392);
  --chart-4: oklch(0.828 0.189 84.429);
  --chart-5: oklch(0.769 0.188 70.08);
  --radius: 0.625rem;
  --sidebar: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: #030213;
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);
}
### Sem usar IA
Trecho de Código CSS:

body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
}

header {
    background-color: #ffb6c1;
    text-align: center;
    padding: 20px;
}

nav {
    background-color: #333;
    text-align: center;
    padding: 10px;
}

nav a {
    color: white;
    margin: 0 15px;
    text-decoration: none;
}
---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Rapidez;
* Integração;
* Colaboração.

### **Limitações**

* Não gera lógica de negócio ou testes.

---

#  **8. Riscos, Custos e Considerações de Uso**

* Dependência de vendor: funcionalidade de IA totalmente integrada e dependente do ecossistema Figma, sem possibilidade de uso fora da plataforma.
* Custos recorrentes: recursos avançados de IA disponíveis apenas em planos pagos, gerando despesa mensal recorrente para uso contínuo.
* Limitações em privacidade ou compliance: execução cloud-first; dados de design e prompts são processados em servidores externos, exigindo avaliação de políticas organizacionais de privacidade e confidencialidade.
* Barreiras técnicas de adoção: necessidade de adaptação do fluxo de trabalho de design para uso de prompts em linguagem natural e maior dependência de funcionalidades automatizadas.
* Dificuldades de execução local: ferramenta exclusivamente baseada em nuvem, impossibilitando uso offline e limitada pela qualidade da conexão com a internet.
* Restrições para fine-tuning ou RAG: não há suporte formal a fine-tuning de modelos ou implementação explícita de pipelines de RAG pelo usuário. 

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para quais atividades de ES? Atividades de levantamento de requisitos visuais, prototipação e validação com stakeholders
* Em quais casos deve ser evitada? Para atividades de implementação, testes ou arquitetura de software.
* Em qual maturidade técnica ela se encontra? madura no contexto de design de interfaces, agregando valor significativo à produtividade de equipes de desenvolvimento.
* Vale a pena para a organização? Vale

---

#  **10. Referências e Links Consultados**

* Documentação oficial: https://www.figma.com/ai/

