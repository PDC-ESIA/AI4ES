# Evidências de integração na Dev UI

As quatro stacks foram exercitadas pelo `workflow_qa`, com detecção automática
do perfil, geração do teste e retorno normalizado.

| Perfil | Geração | Execução | Resultado |
| --- | --- | --- | --- |
| `python-integration` | concluída | 2 testes, 2 sucessos | sucesso |
| `node-integration` | concluída | 2 testes, 2 sucessos | sucesso |
| `java-integration` | concluída | não executada: Maven ausente no ambiente usado | bloqueio ambiental |
| `go-integration` | concluída | teste de integração aprovado | sucesso |

## Sessões completas

| Perfil | Transcrição | Eventos brutos |
| --- | --- | --- |
| `python-integration` | [MD](python-integration-sessao.md) | [JSON](python-integration-sessao.json) |
| `node-integration` | [MD](node-integration-sessao.md) | [JSON](node-integration-sessao.json) |
| `java-integration` | [MD](java-integration-sessao.md) | [JSON](java-integration-sessao.json) |
| `go-integration` | [MD](go-integration-sessao.md) | [JSON](go-integration-sessao.json) |

O bloqueio do Java não impediu a seleção do perfil nem a geração do teste. A
execução depende de Maven ou Gradle disponível no ambiente da Dev UI.

## Validação automatizada

- Matriz real automatizada: 8 testes aprovados (4 integração e 4 E2E smoke).
- Adaptadores de integração do QA: 15 testes aprovados.
