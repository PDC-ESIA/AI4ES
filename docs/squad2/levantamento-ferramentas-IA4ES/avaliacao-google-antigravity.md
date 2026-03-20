# **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                                                              |
| --------------------------------| ---------------------------------------------------------------------------------------------------------------------- |
| **Nome da ferramenta**          | *Google Antigravity*                                                                                                   |
| **Fabricante / Comunidade**     | Google (ecossistema Gemini/DeepMind)                                                                                   |
| **Site oficial / documentação** | [antigravity.google](https://antigravity.google/)                                                                      |
| **Tipo de ferramenta**          | *Agentic IDE* / Plataforma *AI-First* (IDE com Agentes)                                                                |
| **Licença / acesso**            | Proprietária (SaaS): Public Preview Gratuito. Planos Pro/Ultra com rate limits ampliados (feature)                     |

# **2. Informações do Modelo de IA Utilizado**

| Item                           | Descrição                                                                                                                      |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Tipo de IA Generativa**      | LLM Multimodal (Texto + Código + Visão)                                                                                        |
| **Nome do Modelo**             | **Primário:** Gemini 3 Pro (Lançado Nov/2025). **Raciocínio:** Gemini 3 Deep Think. **Opcionais:** Claude Sonnet 4.5, GPT-OSS. |
| **Versão**                     | Gemini 3 Pro                                                                                                                   |
| **Tamanho (nº de parâmetros)** | Não divulgado                                                                                                                  |
| **Acesso**                     | API Gerenciada Google (SaaS). Não permite *Bring Your Own Key* (BYOK).                                                         |
| **Suporte a Fine-tuning**      | Não (no contexto do Antigravity).                                                                                              |
| **Suporte a RAG**              | Não confirmado oficialmente.                                                                                                   |
| **Métodos de prompting**       | Planejamento, Execução e Verificação (agentes com tool use).                                                                   |
| **Ferramentas adicionais**     | Acesso a Editor, Terminal Seguro, Browser Agent (Gemini 2.5 Computer Use).                                                     |

# **3. Contexto de Execução**

| Item                         | Descrição                                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------------------- |
| **Onde roda?**               | *100% Cloud.* Inferência e execução via infraestrutura Google.                            |
| **Infraestrutura utilizada** | Gerenciada pelo Google. Acesso via Web App ou Desktop Electron.                           |
| **Custos**                   | **Preview:** Gratuito com rate limits. **Futuro:** Assinatura Mensal (Pro/Ultra).         |

# **4. Atividades de Engenharia de Software (SWEBOK)**

Para cada item abaixo, descreva:

* **O que a ferramenta faz**
* **Como faz**
* **Exemplos / evidências**
* **Limitações observadas**

Use N/A quando não aplicável.

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações                                                                       |
| ----------------------- | --------------------- | -----------------------------------------------------------------------------------------------|
| Elicitação              | Parcial               | Diálogo com o agente; sem feature oficial de requirements discovery.                           |
| Análise                 | Sim                   | Agentes decompõem solicitações em planos e artifacts.                                          |
| Priorização             | Parcial               | Orientada por instruções do usuário; sem mecanismo nativo de backlog.                          |
| Modelagem               | Parcial               | Pode gerar diagramas em texto, esquema de task/checklist; sem modeladores dedicados (UML/BPMN). |
| Validação / Verificação | Sim                   | Ênfase em "verify" e validação via execução e browser-based computer use.                      |
| Documentação            | Parcial               | Gera artifacts e documentação; qualidade depende bastante do prompt.                           |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações                                        |
| -------------------------------- | --------------------- | --------------------------------------------------------------- |
| Geração de designs arquiteturais | Sim                   | Planejamento e artifacts permitem propor designs arquiteturais. |
| Decisões arquiteturais           | Parcial               | Pode sugerir ADRs; depende da condução do usuário.              |
| Avaliação de trade-offs          | Parcial               | Possível via raciocínio em texto; sem benchmark automático.     | 
| Uso de padrões arquiteturais     | Parcial               | Pode recomendar padrões; sem validação formal embutida.         |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações                                        |
| ---------------------------------- | --------------------- | --------------------------------------------------------------- |
| Sugestão/uso de padrões de projeto | Sim                   | Pode sugerir e aplicar padrões durante codificação/refatoração. |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações                                                |
| ----------------- | --------------------- | ----------------------------------------------------------------------- |
| Geração de código | Sim                   | Confirmado como capacidade agentic (build end-to-end).                  |
| Refatoração       | Sim                   | Agentes operam no editor e terminal permitindo refatorar e iterar.      |
| Detecção de bugs  | Sim                   | Via análise estática e falhas em execução/testes com loops de correção. |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações                                       |
| ------------------------------------------------ | --------------------- | -------------------------------------------------------------- |
| Geração de testes (unit., integração, aceitação) | Sim                   | Capacidade do agente; sem gerador dedicado.                    |
| Execução de testes automatizados                 | Sim                   | Acesso ao terminal e validação por browser-based computer use. |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações                                    |
| --------------------------------- | --------------------- | ----------------------------------------------------------- |
| CI/CD                             | Parcial               | Pode editar pipelines; sem integração CI oficial declarada. |
| Automação                         | Sim                   | Agentes operam autonomamente em tarefas complexas.          |
| Monitoramento                     | N/A                   | Sem observabilidade (APM/logs) embutida.                    |
| Documentação técnica automatizada | Parcial               | Produz artifacts; sem garantia de sincronização automática. |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações                                    |
| ----------------------- | --------------------- | ----------------------------------------------------------- |
| Correções automatizadas | Sim                   | Via loops de execução/erro; depende de permissões e testes. |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações                                       |
| ----------------------------------- | --------------------- | -------------------------------------------------------------- |
| Planejamento                        | Sim                   | Agentes planejam e comunicam via artifacts.                    |
| Execução                            | Sim                   | Agentes executam sobre ferramentas (editor/terminal/browser).  |
| Controle                            | Parcial               | Interação humano-agente; sem dashboards de governança nativos. |
| Encerramento                        | Parcial               | Pode gerar relatórios; sem workflow oficial de closure.        |
| Gestão de riscos                    | Parcial               | Pode auxiliar em análise; sem módulo dedicado.                 |
| Estimativas (tempo, custo, esforço) | Parcial               | Estima em texto; sem telemetria nativa.                        |
| Medição                             | N/A                   | Sem métricas integradas (DORA, etc.).                          |

---

# **5. Qualidade das Respostas**

| Critério                            | Avaliação         | Observações                                                   |
| ----------------------------------- | ----------------- | ------------------------------------------------------------- |
| Precisão                            | ⭐⭐⭐⭐        | Forte com testes/execução; pode degradar em tarefas ambíguas. |
| Profundidade técnica                | ⭐⭐⭐⭐        | Boa para construção end-to-end e planos detalhados.           |
| Contextualização no código/problema | ⭐⭐⭐⭐        | Boa com acesso ao workspace; varia em contextos complexos.    |
| Clareza                             | ⭐⭐⭐⭐        | Artifacts e Walkthrough ajudam a explicar mudanças.           | 
| Aderência às melhores práticas      | ⭐⭐⭐⭐        | Consistente; depende de políticas e revisão humana.           |
| Consistência entre respostas        | ⭐⭐⭐          | Variabilidade percebida em beta (limites, instabilidade).      |
| Ocorrência de alucinações           | Média             | Reduz com "verify"; ainda ocorre em decisões de alto nível.   |

---

#  **6. Experimentos Realizados**

## Descrição das tarefas testadas

Refatoração de uma função de "Adicionar Cliente" de uma implementação manual de lista encadeada dinâmica manualmente de C para Python (depende da implementação).

## Resultados quantitativos
### Usando IA
* Tempo: < 1 minuto.
* Número de erros: 1 (Alucinação na forma como foi implementada a lista, dependendo de um prompt exemplificando como é a implementação).
* Qualidade do código: Alta (Consistente com PEP8 e Padrões de Projeto).
* Cobertura de testes: Alta (>90%). 
* Documentação: Completa (Mostrou os artefatos necessários para rodar o código).

### Sem uso de IA
* Tempo: 8 minutos.
* Número de erros: 5 a 8 (erros de sintaxe, necessitando consulta de doc).
* Qualidade do código: Variável (depende do cansaço do dev).
* Cobertura de testes: Baixa (Geralmente "Caminho Feliz"). 
* Documentação: Totalmente ignorada no rascunho.

## Comentários qualitativos

* Para uma refatoração dessa com contexto melhor e claro com devs mais experientes, em um dia cheio de bugs e refatorações pendentes, no fim do dia realmente traz uma ajuda bastante para o dev ao longo do tempo.

## Exemplos 
* Meu Código:
```python
    def novoCliente(self, cliente):
    novoCliente = Node(cliente)

    if novoCliente is None:
        print("Cliente não foi criado corretamente!")
        return
        
        
    if self.head is None:
            self.head = novoCliente
    else:
        temp = self.head

        while temp.proximo is not None:
            temp = temp.proximo
        
        temp.proximo = novoCliente

    print(f"Novo Cliente (ID: {novoCliente.id}) adicionado com sucesso!")
    sistema.qtdCliente += 1
```
* Código da IA:
```python
def adicionar_cliente(self):
    """Adiciona um novo cliente ao final da lista encadeada."""
    
    novo_cliente = self.criar_cliente()
    
    if novo_cliente is None:
        print("Cliente não foi criado corretamente!")
        return
    
    # Se a lista está vazia, o novo cliente vira a cabeça
    if self.lista_clientes is None:
        self.lista_clientes = novo_cliente
    else:
        # Percorre até o último nó
        temp = self.lista_clientes
        while temp.proximo is not None:
            temp = temp.proximo
        # Adiciona o novo cliente no final
        temp.proximo = novo_cliente
    
    print(f"Novo Cliente (ID: {novo_cliente.id}) adicionado com sucesso!")
    self.qtd_clientes += 1
```
---

# **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**

* Ciclo completo de agente (plan/execute/verify) com coordenação entre editor, terminal e browser.
* Políticas de execução e revisão (presets e permissões granulares) para governança operacional.
* Verificação com navegador e geração de Walkthrough/Media artifacts, melhorando rastreabilidade.
* Disponibilidade de Gemini 3 Pro com completions robustas.

### **Limitações**

* Maturidade de public preview: relatos de instabilidade e variações de fluxo.
* Rate limits dinâmicos por tier (free semanal; Pro/Ultra com renovação periódica).
* Recursos ainda não confirmados oficialmente (suporte a modelos alternativos, RAG formal, BYOK).
* Dependência total de cloud/conectividade.

---

# **8. Riscos, Custos e Considerações de Uso**

* **Dependência de vendor:** inferência e agentes vinculados ao ecossistema Google/Gemini.
* **Custos recorrentes:** Pro/Ultra com quotas ampliadas tornando-se despesa mensal.
* **Privacidade/compliance:** cloud-first com execução automática; requer avaliação de políticas corporativas sobre envio de código.
* **Barreiras técnicas de adoção:** mudança de workflow (agent-first), configuração de políticas e extensões de browser.
* **Dificuldades de execução local:** ferramenta cloud-only; limites afetam uso intensivo.
* **Restrições para fine-tuning ou RAG:** não aparecem como recursos formais da IDE.

---

# **9. Conclusão Geral da Análise**

* **Adequada para:** construção end-to-end com validação (especialmente com testes e fluxos UI verificáveis), refatoração multi-arquivo e ciclos implementar → executar → verificar, aumento de produtividade para construção e refatoração de tarefas repetitivas que o programador SABE o que está fazendo.
* **Evitar em:** projetos ultra-sensíveis sem clareza de compliance, ambientes offline/air-gapped, cenários onde limites de quota impactam entregas.
* **Maturidade técnica:** promissora, porém ainda em public preview com variações de estabilidade.
* **Vale a pena para a organização?** Sim quando há: (a) governança para execução, (b) testes/CI para ancorar validação, (c) ROI que compensa custos Pro/Ultra, (d) verificação de supervisão humana contínua.

---

# **10. Referências e Links Consultados**

* [Google Antigravity — Desenvolvedor oficial](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)
* [Getting Started with Google Antigravity (Codelab)](https://codelabs.developers.google.com/getting-started-google-antigravity)
* [Google AI Pro and Ultra — Rate Limits](https://blog.google/feed/new-antigravity-rate-limits-pro-ultra-subscribers/)
* [Gemini 3 — Blog oficial](https://blog.google/products/gemini/gemini-3/)
* [Gemini 3 for Developers](https://blog.google/technology/developers/gemini-3-developers/)

# **Checklist: Avaliação Inicial de Assistentes de Código**

## **1. Entendimento Geral da Ferramenta**

* [x] **Tipo de interface:** Híbrida (Chat, Slash Commands, Agente Autônomo).  
* [x] **Integração:** IDE Completa (Fork do VS Code) com "Agent Manager".  
* [ ] **Facilidade inicial:** Parcial — exige curva de aprendizado (15 min) para conceito de agente.

## **2. Contexto do Projeto**

* [x] **Lê arquivos automaticamente:** Sim (Indexação automática do workspace).  
* [x] **Entende a stack:** Sim (Detecção via package.json, requirements.txt).  
* [x] **Múltiplas linguagens:** Sim (Polyglot nativo: Python, JS/TS, Rust, Java, Go).

## **3. Modo de Trabalho**

* [x] **Nível de autonomia:** Alto — modifica múltiplos arquivos, executa terminal e operações Git.  
* [ ] **Controle do usuário:** Granular com políticas de permissões e revisão de diffs.  
* [x] **Escopo das ações:** Multi-Arquivo — refatora dezenas de arquivos em uma única task.

## **4. Capacidades Observadas**

* [x] **Completude:** Gera features end-to-end (Código + Teste + Doc).  
* [x] **Explicação:** Gera artifacts visuais explicando mudanças.  
* [ ] **Correção:** Self-healing via loops automáticos (Executa → Falha → Corrige).  
* [ ] **Referências:** Parcial — referencia arquivos internos, mas não cita fontes externas.

## **5. Limitações Importantes**

* [x] **Vinculada a plataforma específica:** Requer Google Cloud para inferência (não roda offline).  
* [ ] **Restrições de linguagem/stack:** Leves — performance inferior em stacks legadas.  
* [ ] **Curva de aprendizado:** Média (5-10h) — adaptação ao fluxo de agentes.

