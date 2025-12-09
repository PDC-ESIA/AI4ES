#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta**          |           Meta Llama                                                                     |
| **Fabricante / Comunidade**     |                Meta Platforms, Inc                                                                |
| **Site oficial / documentação** |                  [Docuemntação Meta Llama](https://llama.developer.meta.com/docs/overview/)                                                              |
| **Tipo de ferramenta**          | LLM de Propósito Geral e Modelo de Fundação (Foundation Model). |
| **Licença / acesso**            |  Modelo de pesos abertos (OpenSource sob uma licença comunitária permissiva para uso comercial e pesquisa)                                              |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa**           | LLM / multimodal / híbrido (arquitetura)                         |
| **Nome do Modelo**                  | ex.:  Llama 2, Llama 3, Llama 4 e variantes especializadas como CodeLlama.|
| **Versão**                          | série Llama 4 (multimodais) e Llama 3.1                                                              |
| **Tamanho (nº de parâmetros)**      | Edge: 1B e 3B (Llama 3.2). Standard: 8B e 70B (Llama 3.1). Massive: 405B (Llama 3.1) para tarefas de alta complexidade.                                                |
| **Acesso**                          | API comercial / Open-source (Pesos Abertos) / Local                          |
| **Suporte a Fine-tuning**           | Sim. É o modelo "padrão" para Fine-tuning e LoRA (Low-Rank Adaptation) na comunidade                     |
| **Suporte a RAG**                   | Sim                                                      |
| **Métodos de prompting suportados** | CoT e In-Context Learning Nativos. ReAct, PoT, Self-Refine via Prompt Engineering                           |
| **Ferramentas adicionais**          | LangChain, LangGraph, Ollama, Groq, extensões VSCode etc.    |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?**                        | Local / Cloud                 |
| **Infraestrutura utilizada no teste** | (GPU (Modelos Grandes), CPU)    |
| **Custos (quando aplicável)**         | Custo por token varia dependendo do provedor de nuvem ou plataforma de hospedagem |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**


---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              |         Sim              | O modelo é frequentemente utilizado para transcrever e resumir reuniões com stakeholders, transformando linguagem natural em requisitos técnicos preliminares. |
| Análise                 |         Sim              |                entende a lógica de sistemas e gera código para renderizadores de diagramas.          |
| Priorização             |         Sim              |                 assistente para processar grandes volumes de dados e aplicar critérios objetivos, como Classificação, Análise de Dependência e Estimativa de Esforço Relativo.          |
| Modelagem               |         Sim              |                modelagem textual que pode ser renderizada visualmente, como gerar diagramas como código, modelagem de dados e modelagem de domínio.          |
| Validação / Verificação |                     Sim  | revisor crítico (QA de requisitos) para garantir que o que foi especificado está correto e alinhado com as necessidades antes de qualquer código ser escrito.|
| Documentação            |         Sim              |                Gera especificações de requisitos e User Stories a partir de rascunhos ou transcrições.          |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Sim                      |        O Llama não gera o arquivo de imagem .png ou .jpg diretamente. Ele gera o código-fonte que ferramentas de renderização transformam em diagramas.                  |
| Decisões arquiteturais           |       Sim                |            Atua como um "assistente de raciocínio", ajudando arquitetos a ponderar prós e contras (ex: Monolito vs. Microserviços) com base em cenários descritos.              |
| Avaliação de trade-offs          |           Sim            |                O modelo não apenas "lista prós e contras", mas consegue ponderar variáveis conflitantes (como Latência vs. Consistência ou Custo de Desenvolvimento vs. Escalabilidade).          |
| Uso de padrões arquiteturais     |             Sim          |                  O Llama não desenha "caixas e setas" diretamente, mas gera a especificação técnica detalhada da arquitetura.        |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Sim                      |      O Llama (especialmente versões focadas em código) consegue sugerir e implementar padrões (como Singleton, Factory, Strategy) em classes existentes.                    |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Sim                      |      É o principal caso de uso do CodeLlama e Llama 3.1, com alta proficiência em Python, JavaScript, C++, etc.                    |
| Refatoração       |             Sim          |                  Utilizado para limpar código, melhorar legibilidade e modernizar sintaxe.        |
| Detecção de bugs  | Sim                      |       Analisa trechos de código para encontrar erros lógicos ou de sintaxe antes da compilação.                    |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) |Sim                       |     Cria casos de teste unitários e de integração automaticamente baseados na lógica da função fornecida.                     |
| Execução de testes automatizados                 |Sim                       |     Auxilia na escrita de scripts para frameworks como Selenium ou Cypress.                     |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             |Sim                       |     Escreve scripts de shell e pipelines de CI/CD (ex: GitHub Actions).                     |
| Automação                         |Sim                       |     O Llama não substitui o Jenkins ou o Kubernetes, mas ele escreve os scripts e configurações que essas ferramentas usam.                     |
| Monitoramento                     | Sim                      |      transforma o monitoramento de uma atividade passiva de visualização de dashboards em uma atividade ativa de inteligência operacional. Atuando principalmente em Detecção, Análise e Remediação.                    |
| Documentação técnica automatizada |                   Sim    |                        Gera docstrings e arquivos README automaticamente analisando o repositório.  |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas |                  Sim     |                        Propõe patches para erros reportados em logs.  |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Sim                      |      reduz a "síndrome da página em branco", gerando esboços robustos de documentos essenciais.                    |
| Execução                            | Sim                      |      o foco do Llama é a comunicação e a remoção de impedimentos através da clareza da informação.                    |
| Controle                            | Sim                      |       o Llama atua na análise de desvios entre o planejado e o realizado.                    |
| Encerramento                        |     Sim                  |              o modelo é excelente para sintetizar conhecimento acumulado, Lições Aprendidas, Relatório final e Arquivamento.|
| Gestão de riscos                    |     Sim                  |          o Llama utiliza seu vasto conhecimento de treinamento para prever problemas que a equipe pode não ter considerado.                |
| Estimativas (tempo, custo, esforço) | Sim                      |      o Llama auxilia na lógica do cronograma no sequenciamento de atividades e detecção de gargalos. Ajuda a realizar análise de custos e justificativa de orçamento.  Pode ler a descrição de uma User Story e sugerir uma pontuação de complexidade (Fibonacci), justificando sua escolha com base nos critérios de aceitação (atuando como um "dev virtual" na votação). Além disso, se alimentado com dados históricos de projetos anteriores (via RAG), pode comparar o projeto atual com os passados para sugerir estimativas de esforço mais precisas.                    |
| Medição                             | Sim                      |      o Llama pode sugerir quais indicadores (KPIs) são mais relevantes para o tipo de projeto atual e ler os números brutos de desempenho gerando uma análise textual explicativa, diagnosticando se a tendência é positiva ou negativa.                    |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐            |extremamente preciso em lógica, matemática e sintaxe de linguagens populares (Python, JS, Java). Em bibliotecas muito específicas ou recentes (pós-corte de conhecimento), ele pode errar parâmetros de funções.             |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            | Llama tende a ser mais explicativo e didático. Ele não apenas dá o código, mas frequentemente explica o porquê daquela escolha arquitetural, descendo ao nível de gestão de memória ou complexidade algorítmica se instigado.            |
| Contextualização no código/problema | ⭐⭐⭐⭐            | Com a janela de 128k tokens, ele mantém o contexto muito bem. A nota não é 5 porque, em prompts massivos com muitas restrições negativas ("não use X"), ele ocasionalmente ignora uma restrição periférica (fenômeno de Lost in the Middle).            |
| Clareza                             | ⭐⭐⭐⭐⭐            | A formatação do Llama é excelente. Ele estrutura respostas com Markdown, negrito e listas de forma muito legível. Separa claramente o que é explicação, o que é código e o que é nota de rodapé.            |
| Aderência às melhores práticas      | ⭐⭐⭐⭐            | Tende a gerar código "Limpo" (Clean Code) e seguro por padrão. Raramente sugere práticas inseguras (como eval()) sem avisos. Às vezes sugere bibliotecas ligeiramente datadas se não for forçado a usar as mais novas.             |
| Consistência entre respostas        | ⭐⭐⭐⭐            | Tende a gerar código "Limpo" (Clean Code) e seguro por padrão. Raramente sugere práticas inseguras (como eval()) sem avisos. Às vezes sugere bibliotecas ligeiramente datadas se não for forçado a usar as mais novas.            |
| Ocorrência de alucinações           | Baixa | Ele agora admite mais frequentemente que "não sabe" ou que não pode acessar URLs externas. Ainda alucina métodos em bibliotecas de nicho ou referências bibliográficas acadêmicas.            |

---

#  **6. Experimentos Realizados**

### ● Descrição das tarefas testadas

Criar uma classe em Python para gerenciar um banco de dados de "Clientes" (CRUD completo)

### ● Resultados quantitativos
#### Uso de IA
* Tempo: < 1 minuto (geração instantânea)
* Número de erros: 0 (código pré-validado, mas possivel de sofrer alucinacoes da LLM)
* Qualidade do código: Alta (segue PEP 8 por padrão)
* Cobertura de testes: N/A (solicitado apenas o código fonte neste passo)
* Comentários qualitativos: Aumento de eficiencia e praticidade se for realizado por profissional com competencia para identificar erros e acertos da IA.

#### Sem uso de IA
* Tempo: 15 - 30 minutos (escrita manual + consulta a doc)
* Número de erros: 2 - 5 (erros de digitação comuns durante o processo)
* Qualidade do código: Variável (depende da disciplina do dev)
* Cobertura de testes: N/A 
* Comentários qualitativos: Ineficiente e demorado, mesmo trabalho poderia ser feito por IA, mas analisado por dev.

### ● Exemplos (copie trechos de código, respostas etc.)
```python
import sqlite3

class ClienteManager:
    """Gerencia operações CRUD para a tabela de Clientes."""

    def __init__(self, db_name="clientes.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.criar_tabela()

    def criar_tabela(self):
        """Cria a tabela se não existir."""
        sql = """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
        """
        self.cursor.execute(sql)
        self.conn.commit()

    def criar_cliente(self, nome, email):
        """Insere um novo cliente no banco."""
        try:
            sql = "INSERT INTO clientes (nome, email) VALUES (?, ?)"
            self.cursor.execute(sql, (nome, email))
            self.conn.commit()
            print(f"Cliente {nome} adicionado com sucesso.")
        except sqlite3.IntegrityError:
            print(f"Erro: O email {email} já está cadastrado.")

    def ler_cliente(self, cliente_id):
        """Retorna os dados de um cliente pelo ID."""
        sql = "SELECT * FROM clientes WHERE id = ?"
        self.cursor.execute(sql, (cliente_id,))
        return self.cursor.fetchone()

    def atualizar_email(self, cliente_id, novo_email):
        """Atualiza o email de um cliente."""
        sql = "UPDATE clientes SET email = ? WHERE id = ?"
        self.cursor.execute(sql, (novo_email, cliente_id))
        self.conn.commit()

    def deletar_cliente(self, cliente_id):
        """Remove um cliente do banco."""
        sql = "DELETE FROM clientes WHERE id = ?"
        self.cursor.execute(sql, (cliente_id,))
        self.conn.commit()
        print(f"Cliente {cliente_id} removido.")

    def fechar_conexao(self):
        self.conn.close()

#Exemplo de uso (Teste manual rápido)

if __name__ == "__main__":
    manager = ClienteManager()
    manager.criar_cliente("Ana Silva", "ana@email.com")
    print(manager.ler_cliente(1))
    manager.fechar_conexao()
```
#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Código aberto / acesso amplo: 
Permite uso comercial, customização, fine-tuning e implantação local sem custos de licença.

* Performance competitiva: 
Modelos Llama 3 e superiores entregam resultados comparáveis a modelos proprietários de grande porte.

* Ecosistema sólido: 
Grande suporte da comunidade, documentação extensa, e integração com frameworks como Hugging Face, LangChain e PyTorch.

* Boa eficiência: 
Pode rodar em hardware mais acessível, com quantizações e otimizações que reduzem o custo operacional.

* Privacidade e controle: 
Organizações podem manter dados sensíveis internamente, sem depender da nuvem de terceiros.

### **Limitações**

* Inferior a modelos fechados de ponta: 
Modelos como GPT-5 e Claude 3 costumam superar o Llama em tarefas complexas, raciocínio profundo, e conversação longa.

* Necessidade de infraestrutura própria: 
Quem instala localmente precisa gerenciar servidores, GPU, monitoramento, segurança e atualizações.

* Fine-tuning pode ser caro e demorado: 
Exige GPUs potentes, bons datasets e know-how, o que nem sempre é simples.

* Menor especialização pronta: 
Muitos casos de uso (ex.: agentes avançados, pesquisa científica, programação complexa) demandam adaptação adicional.

---

#  **8. Riscos, Custos e Considerações de Uso**

## **Riscos**

* Alucinações e respostas incorretas: 
Como todo LLM, não garante precisão absoluta, podendo inventar fatos.

* Vazamento involuntário de dados: 
Sem controles adequados, modelos locais podem registrar ou expor logs sensíveis.

* Riscos de compliance: 
Dependendo da aplicação, pode ser necessário validar conformidade com normas (LGPD, GDPR, SOX etc.).

* Dependência técnica da equipe: 
Projetos podem falhar se não houver equipe qualificada para manter e ajustar o modelo.

* Segurança do modelo: 
Modelos open-source são mais fáceis de examinar e explorar, exigindo cuidado com jailbreaking e abuse cases.

## **Custos**

### **Custos diretos**

* Se rodar na nuvem: custos de GPU por hora.

* Se rodar on-premise: investimento em hardware (GPUs, servidores) + manutenção.

* Se fizer fine-tuning: custo elevado de GPU e preparação de dataset.

### **Custos indiretos**

* Treinamento da equipe

* Desenvolvimento de pipelines de inferência

* Implementação de monitoramento, logging e guardrails

* Segurança e compliance

## **Considerações de Uso**
### **Quando usar**

* Quando você precisa de controle total sobre o modelo.

* Quando quer evitar depender de APIs caras.

* Quando é necessário treinar com dados internos.

* Para produtos embarcados, edge, ou aplicações internas sensíveis.

### **Quando evitar**

* Se você precisa da melhor performance do mercado sem esforço.

* Se não tem equipe para operar modelos localmente.

* Se o projeto exige alta segurança e responsabilidade legal e você não tem governança robusta.
---

#  **9. Conclusão Geral da Análise**

O Meta Llama é uma das melhores opções open-source do mercado, combinando desempenho competitivo, custo reduzido e grande flexibilidade. É ideal para empresas e desenvolvedores que precisam de personalização, controle de dados e infraestrutura própria.

Por outro lado, exige investimento técnico e operacional maior do que simplesmente usar modelos comerciais via API, e nem sempre atinge o nível de raciocínio ou estabilidade dos modelos proprietários mais avançados.

É uma escolha excelente para projetos customizados, laboratórios de IA, ambientes corporativos sensíveis e soluções que precisam rodar localmente, desde que a equipe tenha experiência para operá-lo com segurança.

---

#  **10. Referências e Links Consultados**

- [Llama 3.2 Official Release & Guide](https://www.llama.com/)
- [Llama 3.2 Model Cards (Hugging Face)](https://huggingface.co/docs/transformers/model_doc/llama3)
- [Meta Llama 3.1 - The official Meta Llama website](https://www.llama.com/)
- [Llama 3.1 Technical Overview (IBM/Meta)](https://www.ibm.com/think/news/meta-releases-llama-3-1-models-405b-parameter-variant)
- [Code Llama: Open Foundation Models for Code (arXiv)](https://arxiv.org/abs/2308.12950)
- [Ollama Library - CodeLlama](https://ollama.com/library/codellama)
- [Deep Dive into Llama 3 Architecture](https://towardsdatascience.com/deep-dive-into-llama-3-by-hand-%EF%B8%8F-6c6b23dc92b2/)
- [Decoder-Only Transformer Explained (Hugging Face)](https://huggingface.co/learn/llm-course/chapter1/6)
- [What is Agentic RAG? (IBM)](https://www.ibm.com/think/topics/agentic-rag)
- [Llama-Agents: Multi-Agent Systems Guide](https://www.analyticsvidhya.com/blog/2024/07/llama-agents-agents-as-a-service/)
