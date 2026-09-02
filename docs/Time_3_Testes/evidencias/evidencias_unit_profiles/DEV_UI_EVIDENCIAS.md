# Evidências da Dev UI — testes unitários multistack

Os prints abaixo registram a detecção automática do perfil e a execução dos
testes unitários nas sete configurações suportadas. Caminhos locais com o nome
do usuário foram ocultados; os resultados técnicos foram preservados.

| Perfil | Resultado evidenciado |
| --- | --- |
| `python-pytest` | 10 testes aprovados e 100% de cobertura |
| `node-vitest` | 13 testes aprovados |
| `node-jest` | 13 testes aprovados e 100% de cobertura |
| `node-node-test` | 12 testes aprovados |
| `node-mocha` | 13 testes aprovados |
| `java-junit` | falha inicial corrigida automaticamente; 12 testes aprovados ao final |
| `go-testing` | 21 testes aprovados e 100% de cobertura |

## Python — pytest

Detecção, resultado e cobertura:

![Resultado do perfil python-pytest](dev_ui/python-pytest/01-resultado.png)

Retorno estruturado da execução:

![Execução do perfil python-pytest](dev_ui/python-pytest/02-execucao.png)

## Node/TypeScript — Vitest

Detecção do perfil e resumo:

![Detecção do perfil node-vitest](dev_ui/node-vitest/01-perfil.png)

Retorno estruturado da inspeção:

![Execução do perfil node-vitest](dev_ui/node-vitest/02-execucao.png)

## Node/TypeScript — Jest

Detecção do perfil e resumo:

![Detecção do perfil node-jest](dev_ui/node-jest/01-perfil.png)

Saída do Jest e cobertura:

![Execução do perfil node-jest](dev_ui/node-jest/02-execucao.png)

## Node — node:test

Detecção do perfil e resumo:

![Resultado do perfil node-node-test](dev_ui/node-node-test/01-resultado.png)

Retorno estruturado da execução:

![Execução do perfil node-node-test](dev_ui/node-node-test/02-execucao.png)

Lista de testes executados:

![Saída do perfil node-node-test](dev_ui/node-node-test/03-saida.png)

## Node — Mocha

Detecção do perfil, execução e resumo:

![Detecção do perfil node-mocha](dev_ui/node-mocha/01-perfil.png)

Retorno estruturado da execução:

![Execução do perfil node-mocha](dev_ui/node-mocha/02-execucao.png)

## Java — JUnit

O primeiro ciclo encontrou uma falha de asserção. O Code Fix alterou somente o
teste, reexecutou o JUnit e concluiu com 12 testes aprovados.

![Resultado final do perfil java-junit](dev_ui/java-junit/01-resultado-final.png)

Falha inicial que acionou a autocorreção:

![Falha inicial do perfil java-junit](dev_ui/java-junit/02-falha-inicial.png)

## Go — testing

Detecção do perfil, resultado e cobertura:

![Resultado do perfil go-testing](dev_ui/go-testing/01-resultado.png)

Retorno estruturado da execução:

![Execução do perfil go-testing](dev_ui/go-testing/02-execucao.png)
