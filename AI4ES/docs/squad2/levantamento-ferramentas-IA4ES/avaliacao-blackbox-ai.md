#  **1. Identificação da Ferramenta**

| Item                            | Descrição                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Nome da ferramenta** | Blackbox AI                                                          |
| **Fabricante / Comunidade** | Blackbox AI Inc.                                                     |
| **Site oficial / documentação** | https://blackbox.ai / https://docs.blackbox.ai/                      |
| **Tipo de ferramenta** | Assistente de código e LLM focado em engenharia de software           |
| **Licença / acesso** | Comercial                                                            |

---

#  **2. Informações do Modelo de IA Utilizado**

| Item                                | Descrição                                                    |
| ----------------------------------- | ------------------------------------------------------------ |
| **Tipo de IA Generativa** | Multimodal e Multi-Agent (texto e código)          |
| **Nome do Modelo** | Selecionável (Grok Code Fast, Claude Code Agent, Codex Agent) |
| **Versão** | Depende do modelo selecionado (ex: Claude 3.5, GPT-4o) |
| **Tamanho (nº de parâmetros)** | Não divulgado oficialmente                         |
| **Acesso** | Cloud via Web ou Extensão de IDE                   |
| **Suporte a Fine-tuning** | Não                                                |
| **Suporte a RAG** | Não (Suporte nativo limitado ao contexto do chat)   |
| **Métodos de prompting suportados** | Natural Language, CoT implícito e Instruções de Agente |
| **Ferramentas adicionais** | Extensões VS Code, IntelliJ e integrações com IDEs |

---

#  **3. Contexto de Execução**

| Item                                  | Descrição                               |
| ------------------------------------- | --------------------------------------- |
| **Onde roda?** | Híbrido (Interface Web e Extensões Locais) |
| **Infraestrutura utilizada no teste** | Gerenciada pelo provedor (SaaS) |
| **Custos (quando aplicável)** | Inicial: R$ 27/mês; Pro: R$ 54/mês; Pro Plus: R$ 216/mês |

---

#  **4. Atividades de Engenharia de Software (SWEBOK)**

* **O que a ferramenta faz**: Atua como um copiloto de codificação que gera blocos de código, sugere preenchimentos em tempo real e auxilia no debugging.
* **Como faz**: Analisa o contexto dos arquivos abertos na IDE e os prompts do usuário para gerar respostas em diversas linguagens de programação.
* **Exemplos / evidências**: Geração de funções complexas, explicação de trechos de código legados e correção de erros via comando `/fix`.
* **Limitações observadas**: A versão Cloud possui restrições para repositórios Git vazios e as ações autônomas costumam se limitar a um arquivo por vez.

---

## 4.1. **Requisitos de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Elicitação              | Parcial               | Ajuda a traduzir requisitos textuais em rascunhos de lógica |
| Análise                 | Parcial               | Identifica stacks tecnológicas e sugere dependências |
| Priorização             | N/A                   | Fora do escopo funcional |
| Modelagem               | Parcial               | Sugere estruturas de classes, schemas de banco e DTOs |
| Validação / Verificação | N/A                   | Não possui ferramentas de validação formal de requisitos |
| Documentação            | Sim                   | Gera JSDoc, READMEs e comentários explicativos |

---

## 4.2. **Arquitetura de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Geração de designs arquiteturais | Parcial               | Sugere padrões como MVC ou Microserviços em código |
| Decisões arquiteturais           | Parcial               | Pode comparar bibliotecas e sugerir a melhor stack |
| Avaliação de trade-offs          | N/A                   | Não realiza análise formal de trade-offs arquiteturais |
| Uso de padrões arquiteturais     | Sim                   | Implementa Boilerplates baseados em padrões de mercado |

---

## 4.3. **Design de Software**

| Subatividade                       | Suporte da Ferramenta | Evidências / Observações |
| ---------------------------------- | --------------------- | ------------------------ |
| Sugestão/uso de padrões de projeto | Sim                   | Implementa Singleton, Factory, Observer, etc., sob demanda |

---

## 4.4. **Construção de Software**

| Subatividade      | Suporte da Ferramenta | Evidências / Observações |
| ----------------- | --------------------- | ------------------------ |
| Geração de código | Sim                   | Foco principal: autocomplete e geração de funções |
| Refatoração       | Sim                   | Sugere melhorias de performance e legibilidade |
| Detecção de bugs  | Sim                   | Identifica erros comuns e sugere correções imediatas |

---

## 4.5. **Teste de Software**

| Subatividade                                     | Suporte da Ferramenta | Evidências / Observações |
| ------------------------------------------------ | --------------------- | ------------------------ |
| Geração de testes (unit., integração, aceitação) | Sim                   | Gera suítes de teste (Jest, PyTest, JUnit) automaticamente |
| Execução de testes automatizados                 | N/A                   | A ferramenta não executa o código; apenas gera os testes |

---

## 4.6. **Operações de Software**

| Subatividade                      | Suporte da Ferramenta | Evidências / Observações |
| --------------------------------- | --------------------- | ------------------------ |
| CI/CD                             | Parcial               | Gera arquivos YAML para GitHub Actions ou GitLab CI |
| Automação                         | Parcial               | Cria scripts de automação em Bash ou Python |
| Monitoramento                     | N/A                   | Não aplicável |
| Documentação técnica automatizada | Sim                   | Extrai especificações técnicas diretamente do código |

---

## 4.7. **Manutenção de Software**

| Subatividade            | Suporte da Ferramenta | Evidências / Observações |
| ----------------------- | --------------------- | ------------------------ |
| Correções automatizadas | Sim                   | Comando `/fix` para correção rápida de erros detectados |

---

## 4.8. **Gerenciamento de Projeto de Software**

| Subatividade                        | Suporte da Ferramenta | Evidências / Observações |
| ----------------------------------- | --------------------- | ------------------------ |
| Planejamento                        | Parcial               | Auxilia na quebra de tarefas técnicas |
| Execução                            | Sim                   | Colaboração via compartilhamento de snippets |
| Controle                            | N/A                   | Não possui métricas de controle de projeto |

---

## 4.9. **Gerenciamento de Configuração de Software**

| Subatividade                     | Suporte da Ferramenta | Evidências / Observações |
| -------------------------------- | --------------------- | ------------------------ |
| Identificação de itens           | Parcial               | Indexação de arquivos do repositório local |
| Controle de versões              | N/A                   | Não substitui o Git; atua sobre os arquivos rastreados |

---

#  **5. Qualidade das Respostas**

| Critério                            | Avaliação        | Observações |
| ----------------------------------- | ---------------- | ----------- |
| Precisão                            | ⭐⭐⭐⭐             | Muito alta em linguagens populares (JS, Python) |
| Profundidade técnica                | ⭐⭐⭐⭐             | Depende do modelo/agente escolhido |
| Contextualização no código/problema | ⭐⭐⭐⭐⭐            | Excelente leitura de contexto multi-arquivo |
| Clareza                             | ⭐⭐⭐⭐⭐            | Respostas diretas e código bem formatado |
| Aderência às melhores práticas      | ⭐⭐⭐⭐             | Segue convenções modernas de codificação |
| Ocorrência de alucinações           | Baixa            | Resultados consistentes em tarefas de lógica |

---
## 6. Experimentos Realizados

### ● Geração da estrutura inicial do site a partir de prompts em linguagem natural

### ● Criação do layout visual e identidade do site

### ● Geração e otimização de código CSS para responsividade

### ● Geração de componentes interativos com JavaScript

### ● Refatoração e melhoria da organização do código

---

## Resultados Quantitativos

### Usando IA
- **Tempo:** 5 minutos  
- **Número de erros:** 1  
- **Qualidade do código:** Alta  
- **Cobertura de testes:** Alta  
- **Documentação:** Completa  

---

### Sem uso de IA
- **Tempo:** 2 horas  
- **Número de erros:** Inúmeros  
- **Qualidade do código:** Variável  
- **Cobertura de testes:** Baixa  
- **Documentação:** Totalmente ignorada no rascunho  

---
### ● Exemplos (copie trechos de código, respostas etc.)
### Usando IA

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pedido de Restaurante</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            color: #333;
            display: flex;
            height: 100vh;
        }
        .container {
            display: flex;
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }
        .menu {
            flex: 2;
            padding: 20px;
            background-color: #fff;
            overflow-y: auto;
        }
        .menu h1 {
            font-size: 2rem;
            margin-bottom: 20px;
            color: #d32f2f;
        }
        .dish {
            display: flex;
            margin-bottom: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background-color: #fafafa;
        }
        .dish img {
            width: 100px;
            height: 100px;
            object-fit: cover;
            border-radius: 8px;
            margin-right: 15px;
        }
        .dish-info {
            flex: 1;
        }
        .dish-info h3 {
            margin: 0 0 5px 0;
            font-size: 1.2rem;
        }
        .dish-info p {
            margin: 0 0 10px 0;
            font-size: 0.9rem;
            color: #666;
        }
        .price {
            font-weight: 700;
            color: #d32f2f;
        }
        .add-btn {
            background-color: #4caf50;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .add-btn:hover {
            background-color: #45a049;
        }
        .cart {
            flex: 1;
            padding: 20px;
            background-color: #fff;
            border-left: 1px solid #ddd;
            display: flex;
            flex-direction: column;
        }
        .cart h2 {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #d32f2f;
        }
        .cart-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .cart-item span {
            font-size: 0.9rem;
        }
        .subtotal {
            font-weight: 700;
            margin-top: 20px;
            font-size: 1.1rem;
        }
        .finalize-btn {
            background-color: #d32f2f;
            color: white;
            border: none;
            padding: 15px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 700;
            margin-top: auto;
        }
        .finalize-btn:hover {
            background-color: #b71c1c;
        }
        @media (max-width: 768px) {
            .container {
                flex-direction: column;
            }
            .cart {
                border-left: none;
                border-top: 1px solid #ddd;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="menu">
            <h1>Cardápio</h1>
            <div class="dish">
                <img src="https://via.placeholder.com/100" alt="Pizza Margherita">
                <div class="dish-info">
                    <h3>Pizza Margherita</h3>
                    <p>Massa fina com molho de tomate, queijo e manjericão.</p>
                    <span class="price">R$ 25,00</span>
                    <button class="add-btn" onclick="addToCart('Pizza Margherita', 25)">Adicionar</button>
                </div>
            </div>
            <div class="dish">
                <img src="https://via.placeholder.com/100" alt="Hambúrguer">
                <div class="dish-info">
                    <h3>Hambúrguer Clássico</h3>
                    <p>Carne bovina, queijo, alface e molho especial.</p>
                    <span class="price">R$ 18,00</span>
                    <button class="add-btn" onclick="addToCart('Hambúrguer Clássico', 18)">Adicionar</button>
                </div>
            </div>
            <div class="dish">
                <img src="https://via.placeholder.com/100" alt="Salada Caesar">
                <div class="dish-info">
                    <h3>Salada Caesar</h3>
                    <p>Alface romana, croutons, parmesão e molho caesar.</p>
                    <span class="price">R$ 15,00</span>
                    <button class="add-btn" onclick="addToCart('Salada Caesar', 15)">Adicionar</button>
                </div>
            </div>
        </div>
        <div class="cart">
            <h2>Carrinho</h2>
            <div id="cart-items"></div>
            <div class="subtotal">Subtotal: R$ <span id="subtotal">0,00</span></div>
            <button class="finalize-btn" onclick="finalizeOrder()">Finalizar Pedido</button>
        </div>
    </div>

    <script>
        let cart = [];
        let subtotal = 0;

        function addToCart(name, price) {
            cart.push({ name, price });
            subtotal += price;
            updateCart();
        }

        function updateCart() {
            const cartItems = document.getElementById('cart-items');
            cartItems.innerHTML = '';
            cart.forEach(item => {
                const div = document.createElement('div');
                div.className = 'cart-item';
                div.innerHTML = `<span>${item.name}</span><span>R$ ${item.price.toFixed(2)}</span>`;
                cartItems.appendChild(div);
            });
            document.getElementById('subtotal').textContent = subtotal.toFixed(2);
        }

        function finalizeOrder() {
            alert('Pedido finalizado! Total: R$ ' + subtotal.toFixed(2));
            cart = [];
            subtotal = 0;
            updateCart();
        }
    </script>
</body>
</html>

### Sem usar IA

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Restaurante Bom Sabor</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>

    <header>
        <h1>Restaurante Bom Sabor</h1>
        <p>Faça seu pedido online</p>
    </header>

    <main>
        <h2>Cardápio</h2>

        <div class="cardapio">
            <div class="item">
                <h3>Hambúrguer</h3>
                <p>Pão, carne e queijo</p>
                <span>R$ 25,00</span>
                <button>Adicionar</button>
            </div>

            <div class="item">
                <h3>Pizza</h3>
                <p>Pizza de mussarela</p>
                <span>R$ 40,00</span>
                <button>Adicionar</button>
            </div>

            <div class="item">
                <h3>Refrigerante</h3>
                <p>Lata 350ml</p>
                <span>R$ 6,00</span>
                <button>Adicionar</button>
            </div>
        </div>
    </main>

    <footer>
        <p>© 2026 - Restaurante Bom Sabor</p>
    </footer>

</body>
</html>

---


#  **7. Pontos Fortes e Fracos da Ferramenta**

### **Pontos fortes**
* **Multi-modelo**: Liberdade para trocar o "cérebro" da IA (Grok, Claude, Codex).
* **Integração IDE**: Extensões leves e eficientes para VS Code e IntelliJ.
* **Velocidade**: Respostas rápidas e autocomplete de baixa latência.

### **Limitações**
* **Escopo de modificação**: Frequentemente limitado a um arquivo por interação autônoma.
* **RAG Personalizado**: Falta suporte formal para o usuário subir bases de conhecimento externas.

---

#  **8. Riscos, Custos e Considerações de Uso**

* **Dependência de vendor**: Dependência da plataforma Blackbox AI; interrupções no serviço afetam a produtividade.
* **Custos recorrentes**: Modelo de assinatura mensal que pode ser elevado para grandes equipes (até R$ 216/mês).
* **Privacidade**: Código enviado para processamento em nuvem; risco em empresas com políticas rígidas de segurança.

---

#  **9. Conclusão Geral da Análise**

* A ferramenta é adequada para desenvolvimento acelerado, refatoração de código e debugging assistido.
* Os casos deve ser evitada: Projetos que exigem processamento estritamente local (on-premise).
* Possui maturidade técnica alta, consolidada como um dos principais concorrentes do GitHub Copilot.
* Vale a pena para a organização, pela flexibilidade de agentes e ganho imediato de produtividade.