#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta** | Supermaven                                                                     |
| **Fabricante / Comunidade** | Supermaven Inc. (Fundada por Jacob Jackson, criador do Tabnine)                |
| **Site oficial / documentação** | [supermaven.com](https://supermaven.com)                                       |
| **Tipo de ferramenta** | Assistente de código de baixa latência / Plugin IDE com Long Context           |
| **Licença / acesso** | Híbrido: Freemium (Plano Gratuito generoso e Plano Pro Comercial)              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa** | LLM (Large Language Model) com nova arquitetura de atenção.  |
| **Nome do Modelo** | **Babble** (Modelo proprietário para autocomplete) + Claude 3.5 Sonnet/GPT-4o (Chat). |
| **Versão** | SaaS (Rolling release, atualizações contínuas no servidor).  |
| **Tamanho (nº de parâmetros)** | Não divulgado (Otimizado para inferência rápida).            |
| **Acesso** | API Fechada (Via plugin).                                    |
| **Suporte a Fine-tuning** | **Não** (tradicional). Realiza "In-context Learning" via janela de 1 milhão de tokens. |
| **Suporte a RAG** | **Não.** Substitui RAG por *Long Context* (lê o código todo de uma vez). |
| **Métodos de prompting suportados** | Infill (preenchimento), Chat conversacional.                 |
| **Ferramentas adicionais** | Extensões para VS Code, JetBrains e Neovim.                  |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?** | Cloud (Servidores da Supermaven).       |
| **Infraestrutura utilizada no teste** | GPU Clusters proprietários.             |
| **Custos (quando aplicável)** | Gratuito (Free) ou $10/mês (Pro).       |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              | Baixo / N/A           | Não interage com stakeholders, apenas interpreta intenções do dev. |
| Análise                 | Baixo                 | Pode ajudar a quebrar um problema técnico complexo no chat. |
| Priorização             | N/A                   | Não possui gestão de backlog. |
| Modelagem               | Baixo                 | Não gera diagramas UML ou BPMN. |
| Validação / Verificação | N/A                   | Não valida requisitos de negócio. |
| Documentação            | Médio                 | Gera docstrings e comentários explicando a implementação do requisito. |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Baixo                 | Não projeta sistemas do zero, mas segue a arquitetura existente. |
| Decisões arquiteturais           | Médio                 | O chat pode opinar sobre qual biblioteca usar (ex: SQL vs NoSQL). |
| Avaliação de trade-offs          | Médio                 | Explica prós e contras de abordagens se perguntado no Chat. |
| Uso de padrões arquiteturais     | Alto                  | Identifica o padrão do projeto (ex: MVC) no contexto e sugere código alinhado. |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Alto                  | Sugere implementações corretas de Singleton, Factory, Strategy, etc. via autocomplete. |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Muito Alto            | Ponto forte. Gera funções inteiras com altíssima velocidade e contexto. |
| Refatoração       | Alto                  | Sugere melhorias de legibilidade e modernização de sintaxe. |
| Detecção de bugs  | Médio                 | Identifica erros óbvios de lógica ou tipagem durante a escrita. |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Alto                  | Gera arquivos de testes completos baseados na implementação (Contexto 1M tokens). |
| Execução de testes automatizados                 | N/A                   | A ferramenta gera o código, mas não roda o teste. |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Médio                 | Pode gerar arquivos YAML (GitHub Actions/GitLab CI) se solicitado. |
| Automação                         | Médio                 | Gera scripts de automação (Shell/Python). |
| Monitoramento                     | N/A                   | Não monitora produção. |
| Documentação técnica automatizada | Alto                  | Explica fluxos complexos e gera READMEs baseados no código lido. |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Médio                 | Sugere correções pontuais, mas não aplica patches em massa no sistema. |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | N/A                   | Não aplicável. |
| Execução                            | N/A                   | Não aplicável. |
| Controle                            | N/A                   | Não aplicável. |
| Encerramento                        | N/A                   | Não aplicável. |
| Gestão de riscos                    | N/A                   | Não aplicável. |
| Estimativas (tempo, custo, esforço) | Baixo                 | Pode estimar complexidade de código, mas não horas de trabalho. |
| Medição                             | N/A                   | Não aplicável. |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            | Raramente erra sintaxe devido ao modelo especializado. |
| Profundidade técnica                | ⭐⭐⭐⭐             | Modelo de autocomplete é focado em rapidez; o Chat (Claude) é profundo. |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | **Diferencial:** Janela de 1 milhão de tokens permite entender tudo. |
| Clareza                             | ⭐⭐⭐⭐⭐            | Respostas diretas e código limpo. |
| Aderência às melhores práticas      | ⭐⭐⭐⭐             | Tende a seguir o estilo do código existente no projeto. |
| Consistência entre respostas        | ⭐⭐⭐⭐⭐            | Muito estável. |
| Ocorrência de alucinações           | Baixa            | O contexto massivo reduz drasticamente a invenção de libs inexistentes. |

---

#  **6. Experimentos Realizados**

### Descrição das tarefas testadas
1.  **Geração de CRUD:** Criação de endpoints em Node.js/Express para um sistema de usuários.
2.  **Manutenção de Legado:** Pedido de explicação de uma função complexa em Python que utilizava variáveis globais definidas em outros arquivos.
3.  **Refatoração:** Conversão de uma componente React de Classe para Função (Hooks).

### Resultados quantitativos

* **Tempo com IA x sem IA:** Redução estimada de 40% no tempo de digitação (boilerplate).
* **Número de erros:** Zero erros de sintaxe; 1 erro lógico (importação circular) que foi corrigido no chat.
* **Qualidade do código:** Código gerado seguiu o padrão de indentação e nomenclatura do projeto existente.
* **Comentários qualitativos:** A latência é imperceptível. A sensação é de que a ferramenta "lê sua mente" porque o código aparece instantaneamente, diferentemente do Copilot que tem um leve "delay".

### Exemplos

**Prompt (Implícito/Autocomplete):**
Ao criar um arquivo `user.service.ts` e começar a digitar:
```typescript
import { db } from './db';
// find user by email
```

**Resultado (Supermaven):**
```typescript
export const findUserByEmail = async (email: string) => {
  return await db.user.findUnique({
    where: { email },
    include: { profile: true } // Inferiu corretamente a relação baseada no schema.prisma lido no contexto
  });
};
```

---

#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**
* **Janela de Contexto (1M tokens):** Permite que a IA "veja" o projeto inteiro, reduzindo alucinações e melhorando sugestões de imports.
* **Latência:** Extremamente rápida, focada em não quebrar o fluxo de pensamento do desenvolvedor.
* **Free Tier:** Plano gratuito muito generoso em comparação aos concorrentes.

### **Limitações**
* **Feature Set:** Menos recursos de "Agente" do que concorrentes como Cursor (ex: não tem terminal integrado inteligente ou "Composer" multi-arquivo complexo).
* **Chat:** A interface de chat é funcional, mas básica em comparação ao chat nativo do VS Code ou JetBrains.

---

#  **8. Riscos, Custos e Considerações de Uso**

* **Dependência de vendor:** O modelo central é proprietário. Se a empresa mudar a política de preços, a migração é fácil (apenas trocar plugin), mas perde-se a adaptação ao fluxo.
* **Custos recorrentes:** $10/mês por desenvolvedor no plano Pro (acessível, mas recorrente).
* **Limitações em privacidade:** O código sai da máquina local para a nuvem da Supermaven. Empresas com *compliance* bancário ou governamental estrito podem bloquear o uso.
* **Dificuldades de execução local:** Não roda offline ou localmente (como Ollama/CodeLlama).
* **Restrições para fine-tuning:** Não permite fine-tuning tradicional, mas o contexto longo mitiga essa necessidade.

---

#  **9. Conclusão Geral da Análise**

* **A ferramenta é adequada para quais atividades de ES?** Principalmente **Construção** (Codificação) e **Manutenção** (Entendimento de código legado).
* **Em quais casos deve ser evitada?** Projetos "Air-gapped" (sem internet) ou onde dados sensíveis não podem trafegar para nuvens de terceiros (neste caso, preferir soluções self-hosted).
* **Em qual maturidade técnica ela se encontra?** Alta maturidade em performance e estabilidade, mas média em funcionalidades auxiliares (agentes).
* **Vale a pena para a organização?** Sim, especialmente para equipes que trabalham em bases de código grandes e complexas onde o desenvolvedor perde muito tempo procurando referências em outros arquivos.

---

#  **10. Referências e Links Consultados**

* **Site Oficial:** [https://supermaven.com](https://supermaven.com)
* **Blog Técnico Supermaven:** [https://supermaven.com/blog/context-window](https://supermaven.com/blog/context-window) (Detalhes sobre a arquitetura de contexto de 1 milhão de tokens).
* **Comparativo de Latência:** Testes internos de usabilidade comparando com GitHub Copilot.