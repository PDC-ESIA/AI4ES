# 1. Identificação da Ferramenta

| Item                             | Descrição                                                                       |
| --- | --- |
| *Nome da ferramenta*           | FlutterFlow AI App Generator                                                                     |
| *Fabricante / Comunidade*     | FlutterFlow, Inc.                                                                     |
| *Site oficial / documentação* | [FlutterFlow AI](https://www.flutterflow.io/ai) / [Flutter flow Docs](https://docs.flutterflow.io/)                                                                           |
| *Tipo de ferramenta*           | Plataforma Low-Code com motor de IA para geração de UI (layouts) e lógica (Dart).   |
| *Licença / acesso*             | Freemium. Uso de IA disponível no plano gratuito para testes, com limite de 5 gerações/mês.                                   |

---

# 2. Informações do Modelo de IA Utilizado

| Item                                 | Descrição                                                     |
| --- | --- |
| *Tipo de IA Generativa*           | Baseada em LLM.                         |
| *Nome do Modelo*                   | Não divulgado. |
| *Versão*                           | Não divulgado.                                                             |
| *Tamanho (nº de parâmetros)*       | Não divulgado.                                           |
| *Acesso*                           | Integrado na IDE Web (O usuário interage via prompts nos painéis "Generate with AI").                           |
| *Suporte a Fine-tuning*           | Não exposto ao usuário.                     |
| *Suporte a RAG*                   | Não aplicável/não configurável diretamente (no escopo do teste).                                                       |
| *Métodos de prompting suportados* | Linguagem Natural, Upload de Imagens (Screenshot-to-Code) e integração Figma.                        |
| *Ferramentas adicionais*           | AI Agents (para o produto final, não disponível no plano gratuito).  |

---

# 3. Contexto de Execução

| Item                                   | Descrição                               |
| --- | --- |
| *Onde roda?*                         | **Híbrido**. Design/Geração na Nuvem (Browser). Código gerado roda nativamente (Mobile/Web/Desktop).                 |
| *Infraestrutura utilizada no teste* | Navegador Web (Chrome). Processamento de IA server-side.     |
| *Custos (quando aplicável)*         | IA inclusa no plano grátis. |

---

# Checklist: Avaliação Inicial de Assistentes de Código

## 1. Entendimento Geral da Ferramenta

* [x] Tipo de interface: Chat, autocomplete, comandos ou agente?
    * Interface Visual (Drag-and-Drop) assistida por IA via painéis "Generate with AI" e importação de arquivos/Figma.


* [x] Integração: Funciona dentro do editor/IDE ou é ferramenta separada?
    * Ferramenta separada (IDE proprietária do Flutter Flow).


* [x] Facilidade inicial: Consegui usar nos primeiros 5 minutos sem tutoriais?
    * **Média**. Usar a IA para gerar a primeira tela é instantâneo e fácil. Porém, conectar os dados e configurar a navegação exige entender a lógica visual da ferramenta.



## 2. Contexto do Projeto

* [x] Lê arquivos automaticamente: Preciso colar código ou ela vê o projeto?
    * **Sim**. Capacidade de ler imagens e arquivos de design para converter em componentes funcionais.


* [x] Entende a stack: Detecta linguagens/frameworks ou preciso explicar tudo?
    * Sim. Especializado em Flutter (Frontend) e Dart (Lógica).


* [ ] Múltiplas linguagens: Funciona bem com mais de uma linguagem?
    * Não. Gera código exclusivamente em Dart (Flutter).


## 3. Modo de Trabalho

* [x] Nível de autonomia: Só sugere ou também modifica arquivos sozinha?
    * Apenas cria arquivos conforme solicitado.


* [x] Controle do usuário: Posso revisar antes de aceitar mudanças?
    * Sim. Permite preview e revisão do componente gerado pela IA antes da inserção definitiva no projeto.


* [x] Escopo das ações: Mexe em 1 arquivo por vez ou vários simultaneamente?
    * **Por Componente/Tela**. A IA atua no escopo da tela que está sendo desenhada ou da função que está sendo escrita.



## 4. Capacidades Observadas

* [x] Completude: Gera blocos inteiros de código ou apenas linhas soltas?
    * Gera blocos funcionais completos (Layouts + Funções Dart com imports).


* [ ] Explicação: Possui funcionalidade dedicada para explicar código (botão/comando)?
    * Não possui recurso nativo para explicar o código gerado via chat/botão.


* [x] Correção: Possui comandos explícitos de /fix ou "Debug this"?
    * Não possui comandos de debug/fix; foco estrito em criação/geração.


* [ ] Referências: Cita de onde tirou a informação (fontes) ou gera sem referência?
    * Não aplicável.



## 5. Limitações Importantes

* [x] Vinculada a plataforma específica: Força uso de serviços (ex: AWS, Azure)?
    * O FlutterFlow permite exportar o código fonte e continuar o desenvolvimento localmente, sem depender da plataforma para sempre. Entretanto, a funcionalidade de gerar componentes via IA é perdida fora da plataforma original.


* [x] Restrições de linguagem/stack: Tem tecnologias que não suporta bem?
    * Focado estritamente em Apps Mobile/Web via Flutter. Não serve para criar APIs de Backend complexas (Node.js/Python), apenas consome APIs.


* [x] Curva de aprendizado: Precisa de muito treino pra usar direito?
    * **Média**. A IA acelera o início (UI), mas dominar o gerenciamento de estado e banco de dados requer estudo.
