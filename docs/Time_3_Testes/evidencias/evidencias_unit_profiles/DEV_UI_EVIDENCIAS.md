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

[Ver resultado do perfil python-pytest no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Retorno estruturado da execução:

[Ver execução do perfil python-pytest no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

## Node/TypeScript — Vitest

Detecção do perfil e resumo:

[Ver detecção do perfil node-vitest no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Retorno estruturado da inspeção:

[Ver execução do perfil node-vitest no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

## Node/TypeScript — Jest

Detecção do perfil e resumo:

[Ver detecção do perfil node-jest no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Saída do Jest e cobertura:

[Ver execução do perfil node-jest no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

## Node — node:test

Detecção do perfil e resumo:

[Ver resultado do perfil node-node-test no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Retorno estruturado da execução:

[Ver execução do perfil node-node-test no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Lista de testes executados:

[Ver saída do perfil node-node-test no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

## Node — Mocha

Detecção do perfil, execução e resumo:

[Ver detecção do perfil node-mocha no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Retorno estruturado da execução:

[Ver execução do perfil node-mocha no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

## Java — JUnit

O primeiro ciclo encontrou uma falha de asserção. O Code Fix alterou somente o
teste, reexecutou o JUnit e concluiu com 12 testes aprovados.

[Ver resultado final do perfil java-junit no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Falha inicial que acionou a autocorreção:

[Ver falha inicial do perfil java-junit no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

## Go — testing

Detecção do perfil, resultado e cobertura:

[Ver resultado do perfil go-testing no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)

Retorno estruturado da execução:

[Ver execução do perfil go-testing no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)
