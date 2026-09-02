# Dataset de casos — avaliação do `cr_review_analyzer` (Camada 3)

Cada arquivo `caso_NN_<slug>.json` neste diretório é um caso de referência
usado por `test_reviewer_deteccao_qualidade.py::test_reviewer_contra_dataset`
(um teste parametrizado, um caso = um item de `pytest`). O loader
(`carregar_casos_dataset()`, em `tests/coder_isolado/evals/conftest.py`) lê
todos os `*.json` deste diretório, valida o schema na COLETA (não na
execução — um JSON malformado quebra `pytest --collect-only`, não passa
silenciosamente) e devolve a lista ordenada por `id`.

## Schema

```jsonc
{
  "id": "caso_01_senha_hardcoded",          // único, também usado como ID do teste no pytest
  "categoria": "seguranca",                  // livre — só documentação (seguranca | corretude | testes | codigo_limpo, por convenção)
  "descricao_curta": "...",                  // 1 linha, aparece em relatórios/logs
  "arquivos": {                               // {nome_arquivo: conteúdo} — código principal do caso
    "config.py": "password = \"...\"\n"
  },
  "arquivos_teste": {                         // {nome_arquivo: conteúdo} — teste(s) automatizado(s); {} se o caso testa AUSÊNCIA de teste
    "test_config.py": "..."
  },
  "veredito_esperado": "BLOQUEADO",           // "BLOQUEADO" | "APROVADO" — checado como "## Status: <veredito_esperado>" na saída do reviewer
  "severidade_esperada": "critical",          // severidade da issue principal esperada; null se veredito_esperado == "APROVADO"
  "palavras_chave_deterministicas": [...],    // regexes (case-insensitive); só usadas quando veredito_esperado == "BLOQUEADO" — pelo menos 1 deve casar em "## Issues"
  "problema_para_judge": "..."                // 1-2 frases: o que o LLM-judge usa para avaliar se o reviewer identificou o problema real (ou reconheceu que o código está correto, para casos APROVADO)
}
```

Todas as 9 chaves são obrigatórias em todo caso (mesmo quando o valor é
`{}`, `[]` ou `null`) — o loader falha a coleta se alguma faltar.

O conteúdo de `arquivos`/`arquivos_teste` fica **embutido diretamente como
string no JSON** (não em arquivos `.py` separados) — não porque seja mais
bonito, mas porque assim o caso inteiro (código + teste + expectativa) vive
num único arquivo autocontido, fácil de revisar num PR e sem risco de um
`.py` órfão ficar dessincronizado do `.json` que o referencia.

## Como adicionar um novo caso

1. Copie um `caso_NN_<slug>.json` existente da mesma categoria como ponto de
   partida.
2. Escolha o próximo `NN` livre (2 dígitos, sequencial) e um `slug`
   descritivo em snake_case; `id` = `caso_NN_<slug>` (sem `.json`).
3. Escreva código Python real e sintaticamente válido em `arquivos` — ele
   vai ser lido de verdade pelo Ruff/Bandit (análise estática) e pelo LLM
   revisor real.
4. Se `veredito_esperado` é `"BLOQUEADO"`, preencha
   `palavras_chave_deterministicas` com termos que um reviewer razoável
   usaria para descrever o problema (a Camada 1 do teste falha rápido, sem
   gastar o judge, se nenhum bater) e `severidade_esperada` com a
   severidade que o problema merece (normalmente `"critical"` para
   segurança/corretude/testes ausentes).
5. Se `veredito_esperado` é `"APROVADO"`, deixe `severidade_esperada: null`
   e `palavras_chave_deterministicas: []` — não são usadas nesse caminho.
6. Escreva `problema_para_judge` como uma descrição objetiva do problema
   real (ou, para casos aprovados, uma confirmação de que o código está
   correto) — é isso que o LLM-judge usa como gabarito para decidir se o
   reviewer "acertou".
7. Rode `pytest tests/coder_isolado/evals/ --collect-only -q` para
   confirmar que o novo caso aparece na lista sem erro de schema, antes de
   rodar de verdade (custo real de API).

## Por que dataset separado da lógica de teste

O arquivo Python (`test_reviewer_deteccao_qualidade.py`) contém só a
LÓGICA de avaliação (como rodar o reviewer, como checar o veredito, como
chamar o judge) — genérica para qualquer caso. Os CASOS em si (que código,
que problema, que veredito esperado) vivem em dados (JSON), não em código.
Isso significa:

- Adicionar/editar um caso não exige tocar em Python nem entender
  `pytest.mark.parametrize`/fixtures — é só editar/criar um `.json`.
- Um erro de schema num caso novo é pego na coleta do pytest, antes de
  gastar qualquer chamada de LLM.
- O dataset pode crescer (mais casos, mais categorias) sem inflar o
  arquivo de teste — a suíte de 12 casos vira 30 sem adicionar uma linha
  de lógica nova.
- Fica mais fácil auditar "o que estamos testando" olhando só os `.json`
  (cada um é uma especificação legível do caso), sem precisar ler código
  de teste para entender a cobertura.
