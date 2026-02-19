# 1. Identificação da Ferramenta

| Item                            | Descrição                                                                      |
|---------------------------------|--------------------------------------------------------------------------------|
| *Nome da ferramenta*          | Github Copilot                                                                   |
| *Fabricante / Comunidade*     | GitHub                                                                           |
| *Site oficial / documentação* | https://github.com/features/copilot?locale=pt-BR                                 |
| *Tipo de ferramenta*          | Assistente de código / Plugin de IDE / Plataforma multimodal                     |
| *Licença / acesso*            | Comercial                                                                        |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                | Descrição                                                    |
|-------------------------------------|--------------------------------------------------------------|
| *Tipo de IA Generativa*           | Multimodal                                                     |
| *Nome do Modelo*                  | Claude Haiku 4.5, Claude Opus 4.5 (Preview), Claude Sonnet 4, Claude Sonnet 4.5, Gemini 2.5 Pro, Gemini 3 Pro (Preview), GPT-4.1, GPT-4o, GPT-5, GPT-5 mini, GPT-5-Codex (Preview), GPT-5.1 (Preview), GPT-5.1-Codex (Preview), GPT-5.1-Codex-Max (Preview), GPT-5.1-Codex-Mini (Preview), GPT-5.2 (Preview), Grok Code Fast 1, Raptor mini (Preview), dentre outros à escolha do usuário.                                           |
| *Versão*                          | 0.35.0                                                         |
| *Tamanho (nº de parâmetros)*      | Depende do modelo selecionado                                  |
| *Acesso*                          | Plugin Instalado no editor de código/IDE, site do GitHub, CLI  |
| *Suporte a Fine-tuning*           | Parcialmente                                                   |
| *Suporte a RAG*                   | Não                                                            |
| *Métodos de prompting suportados* | ???                                                            |
| *Ferramentas adicionais*          | Chat integrado à IDE, autocomplete contextual, sugestões inline, edição multi-arquivo assistida, explicação de código, geração de testes, comandos de refatoração                                                            |

---

# 3. Contexto de Execução

| Item                                  | Descrição                               |
|---------------------------------------|-----------------------------------------|
| *Onde roda?*                          | Cloud                                   |
| *Infraestrutura utilizada no teste*   | Plugin no VSCode                        |
| *Custos (quando aplicável)*           | USD 10 / mês                            |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

- [X] Tipo de interface: Chat, autocomplete, comandos ou agente?
- [X] Integração: Funciona dentro do editor/IDE ou é ferramenta separada?
- [X] Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?

## 2. Contexto do Projeto

- [X] Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto? **Vê o projeto**
- [X] Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo? **Detecta automaticamente**
- [X] Múltiplas linguagens: Funciona bem com mais de uma linguagem?

## 3. Modo de Trabalho

- [X] Nível de autonomia: Só sugere ou também modifica arquivos sozinha? **Depende da forma que for utilizada**
- [X] Controle do usuário: Posso revisar antes de aceitar mudanças?
- [X] Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente? **Vários de forma simultânea**

## 4. Capacidades Observadas

- [X] Completude: Gera blocos inteiros de código ou apenas linhas soltas? **Blocos completos**
- [X] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?
- [X] Correção: Possui comandos explícitos de /fix ou "Debug this"?
- [0] Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?

## 5. Limitações Importantes

- [X] Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)? **GitHub**
- [0] Restrições de linguagem/stack: Tem tecnologias que não suporta bem? **Nenhuma informada até o momento**
- [0] Curva de aprendizado: Precisa de muito treino pra usar direito? **Uso fácil**

#  **6. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo, descreva:

* **O que a ferramenta faz**
* **Como faz**
* **Exemplos / evidências**
* **Limitações observadas**

Use N/A quando não aplicável.

---

## 6.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              | Parcial                      | Pode transformar prompts em requisitos                         |
| Análise                 | Parcial                      | Pode comparar os requisitos                          |
| Priorização             | Parcial                      | A depender do prompt                         |
| Modelagem               | Parcial                      | Pode gerar artefatos de modelagem via código mermaid/plantUML                         |
| Validação / Verificação | Parcial                      | Pode comparar com requsitos/histórias de usuário                         |
| Documentação            | Suporta                      | Pode ler e gerar documentações com base no código                        |

---

## 6.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Suporta                      | Consegue entender e realizar                         |
| Decisões arquiteturais           | Suporta                      | Consegue entender e realizar                         |
| Avaliação de trade-offs          | Suporta                      | Consegue entender e realizar                         |
| Uso de padrões arquiteturais     | Suporta                      | Consegue entender e realizar                         |

---

## 6.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Suporta                      | Consegue entender e realizar                         |

---

## 6.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Suporta                      | Objetivo principal da ferramenta                         |
| Refatoração       | Suporta                      | Objetivo principal da ferramenta                         |
| Detecção de bugs  | Suporta                      | Objetivo principal da ferramenta                         |

---

## 6.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Suporta                      | Pode utilizar bibliotecas de testes ex.: Jest                          |
| Execução de testes automatizados                 | Não Suporta                      | Pode ensinar a executar e gerar testes automatizados                         |

---

## 6.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | N/A                      | O modelo é um code assistant                         |
| Automação                         | N/A                      | O modelo é um code assistant                         |
| Monitoramento                     | N/A                      | O modelo é um code assistant                         |
| Documentação técnica automatizada | N/A                      | O modelo é um code assistant                         |

---

## 6.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | N/A                      | O modelo é um code assistant                         |

---

## 6.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | N/A                      | O modelo é um code assistant                         |
| Execução                            | N/A                      | O modelo é um code assistant                         |
| Controle                            | N/A                      | O modelo é um code assistant                         |
| Encerramento                        | N/A                      | O modelo é um code assistant                         |
| Gestão de riscos                    | N/A                      | O modelo é um code assistant                         |
| Estimativas (tempo, custo, esforço) | N/A                      | O modelo é um code assistant                         |
| Medição                             | N/A                      | O modelo é um code assistant                         |

---

#  **7. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐⭐            | Respostas geralmente corretas para padrões conhecidos, APIs populares e boas práticas consolidadas. Erros são raros e normalmente ligados a regras de negócio não explícitas.            |
| Profundidade técnica                | ⭐⭐⭐⭐⭐            | Demonstra bom domínio de estruturas de código, padrões de projeto, testes, refatoração e arquitetura comum. Limitação em discussões teóricas profundas quando comparado a LLMs focados em pesquisa.            |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | Excelente uso do contexto do projeto aberto na IDE, incluindo múltiplos arquivos, dependências e padrões existentes no repositório.            |
| Clareza                             | ⭐⭐⭐⭐⭐            | Código gerado é legível, organizado e geralmente segue convenções da linguagem e do projeto. Comentários e nomes de variáveis são claros.            |
| Aderência às melhores práticas      | ⭐⭐⭐⭐⭐            | Aplica princípios como SOLID, separação de responsabilidades, testes automatizados e linting, quando o contexto permite.            |
| Consistência entre respostas        | ⭐⭐⭐⭐              | Pode variar levemente conforme o modelo selecionado (GPT, Claude, Gemini), mas mantém coerência geral dentro da mesma sessão.            |
| Ocorrência de alucinações           | Baixa                   | Ocorre principalmente ao assumir comportamentos de bibliotecas pouco comuns ou versões muito recentes. Geralmente mitigável com prompts mais específicos.            |

---

#  **8. Experimentos Realizados**

### ● Descrição das tarefas testadas

Desenvolvimento de calculadora de IMC em Java

### ● Resultados quantitativos

* Com IA
    * Tempo para solucionar: 01 minuto e 21 segundos

* Sem IA
    * Tempo para solucionar: 06 minutos e 43 segundos

### ● Exemplos (copie trechos de código, respostas etc.)

* Código com IA

```Java

    void main() {
    Scanner scanner = new Scanner(System.in);

    float wheight, height, IMC;

    System.out.print("Digite o seu peso (kg): ");

    wheight = scanner.nextFloat();

    System.out.print("Digite a sua altura (m): ");

    height = scanner.nextFloat();

    IMC = wheight / (height * height);

    System.out.printf("O seu IMC é: %.2f\n", IMC);

}

    
```

* Código sem IA

```Java

    import java.util.Scanner;

    void main() {
        Scanner scan = new Scanner(System.in);
        float weight, height, IMC;

        System.out.println("Qual é o seu peso? (em Kg)");

        weight = scan.nextFloat();

        System.out.println("Qual é a sua altura? (em m)");

        height = scan.nextFloat();

        IMC = weight / (height * height);

        System.out.printf("O seu imc é igual a: %.2f", IMC);
    }
    
```

#  **9. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Integração profunda com IDE (baixo atrito)
* Forte entendimento de contexto de projeto
* Excelente para refatoração e testes
* Suporte a múltiplas linguagens e stacks
* Redução significativa de esforço cognitivo em tarefas repetitivas

### **Limitações**

* Dependência total do ecossistema GitHub
* Não cita fontes ou justificativas formais
* Pode gerar código “correto” mas desalinhado à regra de negócio
* Não executa código nem valida resultados
* RAG e fine-tuning não disponíveis ao usuário final

---

#  **10. Riscos, Custos e Considerações de Uso**

* Dependência de vendor: Alta (GitHub/Microsoft)
* Custos recorrentes: USD 10/mês por desenvolvedor
* Privacidade: Código enviado à nuvem (atenção a projetos sensíveis)
* Compliance: Pode ser problemático em ambientes regulados
* Execução local: Não disponível
* Customização avançada: Limitada (sem RAG/fine-tuning direto)

---

#  **11. Conclusão Geral da Análise**

* Adequada para:
    * Construção de software, refatoração, testes, documentação técnica e apoio a design/arquitetura.
* Deve ser evitada quando:
    * Regras de negócio são altamente específicas
    * Código é extremamente sensível (segurança/compliance)
    * É necessária rastreabilidade formal de decisões
* Maturidade técnica:
    *  Alta para engenharia de software prática
    *  Média para processos formais de ES

* Vale a pena para a organização?
    * Sim, especialmente para equipes de desenvolvimento, desde que usada como assistente, não como substituto de revisão humana.

---

#  **12. Referências e Links Consultados**

* Documentação oficial do GitHub Copilot
    * https://github.com/features/copilot
* GitHub Copilot Trust Center
    * https://github.com/trust-center
* Relatos técnicos da comunidade (GitHub Issues, blogs)
* Experiência prática em IDE (VSCode)