# Agente Revisor de PRs (PR Revisor Agent)

Este módulo contém um agente autônomo desenvolvido utilizando o Google ADK (Agent Development Kit). Seu objetivo é atuar como um revisor de código automatizado, analisando as diferenças (`git diff`) de um Pull Request e gerando um relatório com base em critérios de qualidade de software (Clean Code, SOLID e Testes).

## Estrutura do Agente
- `agent.py`: Arquivo principal de configuração do agente e definição do LLM (Mistral).
- `prompts/pr_revisor.py`: Contém as instruções de sistema, o papel do agente e as diretrizes de qualidade de código.
- `tools/tools_revisao.py`: Ferramentas que o agente pode utilizar (ler o `git diff` e salvar o relatório em `.md`).
- `test_revisor.py`: Script de execução Headless (sem interface), usado como ponto de entrada para testes e uso desse agente.

## Como Utilizar

Este agente possui dois modos de execução, dependendo do seu objetivo:

### Modo 1: Teste Manual / Interface Visual (Dev UI)
Ideal para debugar ou testar o agente interagindo via chat.

1. Suba o servidor do ADK **A PARTIR DA RAIZ DO PROJETO**:
    ```
   uvicorn main:app --reload --port 8081
    ```

2. Acesse a interface no navegador para abrir o adk web: `http://127.0.0.1:8081/dev-ui/?app=pr_revisor_agent`
3. Envie o prompt inicial para disparar a auditoria.

### Modo 2: Automação / Pipeline CI/CD (Headless)
Ideal para integração contínua (GitHub Actions, GitLab CI, etc.). Este modo roda o agente silenciosamente, gera o relatório e emite um **Exit Code** para o sistema operacional, permitindo o bloqueio automático de PRs.

**Comando de Entrada:**<br>
Na raiz do projeto (`adk/`), para testar se a ferramenta está funcionando como deveria, execute o script abaixo.
E, para a integração, deve embutir esse exato comando dentro do código da infraestrutura do código(da task que você está fazendo para integrar o agente):

```bash
python -m src.agents.pr_revisor_agent.test_revisor
```

**Contrato de Saída (Exit Codes):**<br>
O script analisa o artefato gerado (`doubt_artifact_revisao.md`) e retorna os seguintes códigos para a máquina:

- `Exit Code 0` **(Sucesso):** O código foi lido e o status final no relatório é `APROVADO`. O pipeline pode liberar o Merge.
- `Exit Code 1` **(Falha):** O código não atendeu aos requisitos ou houve erro na execução. O pipeline deve **bloquear** o Merge.

### Pré-requisitos
Certifique-se de que sua API Key está configurada no arquivo `.env` na raiz do projeto:

```env
MISTRAL_API_KEY="sua_chave_aqui"
```
