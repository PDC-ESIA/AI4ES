# Revisão dos falsos positivos do validador (SWE-bench Verified, run `gemini-3.7-flash`)

Issue: #417 · Relatório principal: [swebench-relatorio.md](swebench-relatorio.md) (seção 4.2 e pontos A2 e A3 da seção 5)

Este documento revisa, **uma a uma**, as 5 instâncias em que o
`implementation_validator` aprovou o loop e o harness oficial do SWE-bench
reprovou a solução (falsos positivos da métrica 3): `django__django-11400`,
`django__django-11734`, `django__django-14034`,
`matplotlib__matplotlib-20859` e `pylint-dev__pylint-7080`. A pergunta de
cada revisão é: **por que a aprovação estava errada, e o validador poderia ter
percebido?**

## 1. Método

Toda a análise foi feita **sem nenhuma chamada ao LLM**. Para cada instância, foram
lidos:

1. a issue (`problem_statement`) e o **patch oficial** e os **testes oficiais**
   (`test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`) do dataset;
2. o **patch do coder** (`patches/<id>.diff`) e a lista do que foi excluído dele;
3. o **registro da execução** no `progress.jsonl`: comando de teste declarado,
   contagem de testes, notas por rodada, veredito e o texto final do coder;
4. o **resultado oficial**: `report.json` e `test_output.txt` do harness.

Além da leitura, as conclusões foram **verificadas por execução** na imagem oficial
de cada instância (`swebench/sweb.eval.x86_64.<id>`): aplicando o patch do coder, o
oficial ou trechos do oficial, rodando consultas e testes e, em um caso, reavaliando
o patch com o `run_evaluation` do harness oficial. Essas execuções foram feitas à mão
e **não são versionadas**; o que cada uma mostrou está descrito na seção da
instância.

Todos os arquivos do run estão em
`benchmarks/coding_review/swebench/results/run_20261001_122939_github_copilot-gemini-3.7-flash_n30/`.
O dataset (`datasets/`) e os logs brutos do harness (`grading/logs/`) são locais
e não são versionados; o que dependeu deles está indicado em cada seção.

Cada revisão foi conferida por um subagente independente (o "revisor", que refez as
verificações por conta própria), e o que ele apontou e o que mudou está registrado
no fim da seção. O "autor" é quem escreveu a análise. As tabelas de revisão estão em
primeira pessoa ("eu havia escrito") porque registram correções do próprio autor. Uma
revisão final conferiu a consistência do documento inteiro.

## 2. Taxonomia das causas

Cada caso recebe uma **causa primária** e, se houver, **causas secundárias**: as
causas não são mutuamente exclusivas.

| Código | Causa | Significa |
| ------ | ----- | --------- |
| **C1** | Issue subespecificada ou enganosa | O texto da issue leva a uma solução diferente da que o teste oficial exige |
| **C2** | Solução incorreta ou incompleta | O bug continua, ou só parte dele foi corrigida, e os testes do coder não o exercitavam |
| **C3** | Regressão | O **código de produção** da solução quebra comportamento que já funcionava, **mesmo que fora do `PASS_TO_PASS`**. O P2P do SWE-bench cobre só os arquivos de teste que o patch oficial toca; uma regressão em outro módulo só aparece rodando uma suíte maior |
| **C4a** | Gabarito sobre-específico | O teste oficial reprova por exigir um detalhe da solução original que o texto da issue não pede |
| **C4b** | Teste ou ambiente instável | O teste oficial é não determinístico (por exemplo, dependente do tempo) ou o ambiente falha, de modo que a reprovação pode não se repetir |
| **C5** | Teste existente alterado | Para a suíte passar, o coder mudou a expectativa de um teste que já existia, para acomodar a própria mudança (no código de produção ou num fixture de teste). Se a mudança de fixture quebra testes existentes no run oficial, o efeito aparece como falha em `PASS_TO_PASS`, mas é classificado aqui, e não como C3, porque o comportamento de produção não regrediu |

**Rótulo instável** não é uma causa, e sim um atributo à parte: a instância foi
reprovada no run, mas a reavaliação do mesmo patch com o harness oficial **aprova**.
Registra-se como "reprovada no run; N reavaliações, k reprovações". Só se trata a
instância como "provavelmente não é falso positivo real" quando **k = 0 com N ≥ 3** e
a causa identificada é do tipo C4b. Mesmo assim a conclusão é provisória: poucas
reavaliações não excluem uma taxa de falha relevante (com 0 reprovações em 3
tentativas, o limite superior de 95% da taxa de falha é de ~63%; em 5, ~45%).
A métrica 3 do relatório principal **segue o resultado do run**.

**Fator de ambiente** também é um atributo, e não uma causa: o executor não fica
verde com o arquivo de testes inteiro da instância, nem mesmo com a solução oficial
(as 4 instâncias do `--executor-sanity`, ver B1 no relatório). Isso não causa o
conserto errado, mas **permite a aprovação**, porque obriga o coder a estreitar o
comando de teste até ele ficar verde.

Para cada caso, registra-se também se a aprovação era **evitável pelo
validador**, isto é, se havia, no que o loop tinha à mão (código, documentação,
testes do repositório e evidências do executor), um sinal que justificasse
reprová-la, e **de que forma** (por exemplo, ampliando o escopo de testes).

## 3. Resumo

### 3.1 Quadro geral

| Instância | Causa primária | Causas secundárias | Evitável pelo validador? | Resultado em 1 frase |
| --------- | -------------- | ------------------ | ------------------------ | -------------------- |
| `django-14034` | C1 (issue enganosa) | C3 (regressão fora do P2P) | Em princípio sim, indiretamente (rodar a suíte maior) | O coder seguiu o texto da issue e quebrou um teste existente; o oficial exige outra correção |
| `django-11400` | C2 (incompleta) | C5 (teste existente alterado) | Em um ponto (C5), sem resolver a instância | Consertou só o caminho direto; ajustou a expectativa de um teste para passar |
| `django-11734` | C2 (incompleta) | C1 | Dificilmente | A exceção sumiu, mas o resultado ficou errado em silêncio num caso que a issue não mostra |
| `matplotlib-20859` | C4b (teste instável) | n/a | Não se aplica | Patch equivalente ao oficial; reprovado por teste dependente do relógio; **rótulo instável** |
| `pylint-7080` | C1 (issue não reproduz) | C2, C3 (menor) | Em princípio sim, por inspeção ou exigindo "vermelho antes" | O comando da issue não reproduz; o conserto não altera o cenário do defeito; fator de ambiente (atributo) |

### 3.2 O que as cinco revisões mostram

1. **Só um dos cinco é provavelmente um falso positivo "de mentira".** A
   `matplotlib-20859` tem patch equivalente ao oficial, e o mesmo patch resolveu em 5
   de 5 reavaliações oficiais. Os outros quatro são soluções realmente erradas que o
   loop aprovou: duas correções incompletas (`11400`, `11734`), uma que contradiz o
   contrato do projeto (`14034`) e uma sem efeito sobre o defeito (`pylint-7080`). A
   conclusão sobre a `20859` é provisória (ver "rótulo instável" na seção 2).
2. **Nos quatro erros reais, os testes que o coder rodou não exercitavam o defeito que
   o oficial cobra.** Na `11400`, os dois testes novos cobriam só o caminho direto. Na
   `11734`, o teste do coder passava com o patch dele e o oficial não, logo era mais
   fraco. Na `pylint-7080`, a rodada final só rodou 5 testes pré-existentes que passam
   sem conserto algum. Na `14034`, o teste do coder (de conteúdo desconhecido, então
   isto é inferência) só poderia cobrir a interpretação dele, e a regressão estava num
   teste que ele não rodou. Na `matplotlib-20859`, ao contrário, o teste do coder
   cobre o defeito da issue e o patch está correto. O validador aprova pelo estado da
   suíte que o **próprio coder** escolheu, então a qualidade dessa suíte decide a
   qualidade da aprovação.
3. **O texto da issue não bastava em 3 dos 5 casos** (`14034`, `11734` e
   `pylint-7080`, todas com C1). Nos três, o `hints_text` do dataset, que o benchmark
   **não** entrega ao coder, mostra que o problema real era outro: o comportamento
   relatado era o projetado (`14034`), o `ValueError` do texto já estava corrigido
   (`11734`), ou o comando da issue não reproduz o defeito (`pylint-7080`).
4. **O `PASS_TO_PASS` do SWE-bench não pega regressões em módulos que o patch oficial
   não toca.** Na `14034`, a suíte `forms_tests` completa tem 1 erro novo com o patch
   do coder, que o P2P (12 testes, um módulo) não vê. Na `pylint-7080`, há uma
   regressão de borda na resolução de imports que nenhum teste cobre. Isso significa
   que o "resolvido" oficial é, por construção, uma verificação limitada.
5. **Havia um sinal acionável e discriminante em 3 dos 5 casos, mas não encontrei
   verificação equivalente no loop:** rodar uma suíte maior que a escolhida pelo coder
   (`14034`); detectar que um teste pré-existente teve a expectativa alterada na
   rodada em que a nota ficou verde (`11400`); exigir que algum teste falhe sem o
   conserto, ou revisar o diff de produção contra o código existente, por exemplo um
   filtro que já é aplicado adiante (`pylint-7080`). Na `11734` há sinais fracos
   (`testes_nao_identificados`, um `texto_final` sem a descrição do conserto), mas
   nenhum discriminante; e na `20859`, a aprovação provavelmente estava certa.
6. **Dois casos têm coincidências literais com o upstream**: na `11400`, os nomes de
   dois testes novos e o trecho de `Field.get_choices`, idêntico linha a linha ao oficial; na
   `11734`, o trecho de `split_exclude`, também idêntico linha a linha ao oficial. Pode ser acaso ou memorização do modelo, e os
   registros não permitem distinguir (ver A10 no relatório). Na `20859`, a
   coincidência é explicada pela própria issue, que sugere a correção.

### 3.3 O que isso muda na leitura da métrica 3

A taxa de falsos positivos do relatório principal (5/24, 20,8%) **mistura causas
diferentes**: um provável rótulo instável (`20859`, que levaria a 4/24 = 16,7%, IC 95%
6,7% a 35,9%, se fosse corrigido) e soluções realmente erradas. O que os registros mostram é que a
**evidência apresentada pelo coder era fraca ou mal direcionada**. Não é possível
separar isso de um validador permissivo, porque a entrada que o validador recebeu não
foi guardada (ver 4.5, 5.9, 6.9 e 8.9). Há ainda um sexto caso fora dessas cinco: a `django-12125`, o único falso negativo do run (seção 9). A pergunta útil passa a ser não só "o validador
erra?", mas "**o que o loop exige do coder como prova**?".

### 3.4 Hipóteses para trabalho futuro (fora do escopo da #417)

A #417 mede e **não altera** o executor, o validador nem a `loop_policy`. As ideias
abaixo são **hipóteses**, cada uma a medir antes de qualquer mudança, e caberiam em
issues separadas:

1. Conferir, no executor, se testes pré-existentes tiveram a expectativa alterada na
   rodada em que a suíte ficou verde (`11400`).
2. Exigir uma verificação "vermelho antes, verde depois" para o teste que o coder
   escreveu (`pylint-7080`; na `11734` não se mostra que ajudaria, ver 6.8).
3. Rodar, além do comando escolhido pelo coder, uma suíte maior do módulo alterado
   (`14034`).
4. Revisar o diff de produção contra o código existente, por exemplo para achar um
   filtro que já é aplicado adiante (`pylint-7080`).
5. Registrar, para análise, a entrada do validador, a transcrição do coder e os
   arquivos de teste que o benchmark exclui do patch (hoje não são preservados).

### 3.5 Limites do conjunto

São 5 casos de um run, de um modelo, e a análise é qualitativa: os padrões acima são
hipóteses, e não estimativas de frequência. A variância da correção oficial só foi
medida para uma instância (`matplotlib-20859`), então os demais rótulos podem ter
alguma instabilidade que não foi verificada.

## 4. `django__django-14034`

### 4.1 Em uma frase

O coder implementou o que o **texto** da issue sugere (`is_valid()` falso para
um campo composto opcional), mas isso **contradiz o contrato documentado do
Django** e quebra um teste que já existia no repositório; o teste oficial, por
sua vez, exige outra correção, na renderização do atributo HTML `required`. Causa
primária **C1** (issue enganosa), secundária **C3** (regressão fora do P2P). A
aprovação era evitável, mas não pelo motivo que o teste oficial revela.

### 4.2 O que a issue pede

A issue (`MultiValueField ignores a required value of a sub field`) descreve um
campo com `required=False` e `require_all_fields=False`, com um subcampo
obrigatório. Com os dois valores vazios, `form.is_valid()` retorna `True`, e o
autor "espera" `False`, porque um subcampo é obrigatório. Termina com "If above
behavior is not expected, please fix this problem", ou seja, o próprio autor não
tem certeza de que o comportamento seja um defeito. **Nada no texto da issue
menciona o atributo HTML `required`.**

O `hints_text` do dataset (que o benchmark **não** entrega ao coder) traz a
discussão do ticket. Nela, um mantenedor escreve que "a form with every subfield
empty on an optional MVF should pass validation, and it does, and there is a test
in the suite for it. (The implication in the body of the ticket is not quite
right.) So I suggest the linked patch avoid making changes to validation", e
propõe renomear o ticket para focar no atributo HTML `required`.

### 4.3 O que o teste oficial exige

O patch oficial muda `django/forms/boundfield.py` (`build_widget_attrs`): quando
`require_all_fields` é falso e o widget é um `MultiWidget`, passa a marcar o
atributo `required` de cada subwidget conforme o `required` do respectivo
subcampo. Não toca em `django/forms/fields.py`, onde está a validação.

O único teste que deveria passar (`FAIL_TO_PASS`) é
`test_render_required_attributes`. Ele usa um campo com **`required=True`**,
`require_all_fields=False` e subcampos `(required=True, required=False)`, e
verifica que o HTML renderizado traz `required` só no primeiro `<input>`. A
configuração difere da da issue (`required=False` no campo composto), e o que se
verifica é o HTML. Com o patch oficial, o exemplo da própria issue **continua**
retornando `is_valid() == True`: a correção oficial rejeitou a interpretação
"esse exemplo deve ser inválido".

### 4.4 O que o coder fez

Alterou `MultiValueField.clean()` em `django/forms/fields.py` (6 linhas
adicionadas). Quando todos os valores estão vazios, `required=False` e
`require_all_fields=False`, agora percorre os subcampos e, se algum é
obrigatório, levanta `ValidationError` com a mensagem `incomplete`. **Verificado
por execução** (imagem oficial da instância, patch do coder aplicado sem
conflito):

| Cenário | Base | Patch do coder | Patch oficial |
| ------- | ---- | -------------- | ------------- |
| Exemplo da issue (ambos vazios) | `True` | `False` | `True` |
| Formulário sem as chaves do campo (`F({})`) | `True` | `False` | `True` |

O patch do coder faz o exemplo da issue retornar o que o texto pede, mas alterou
um comportamento que o código anterior tratava de propósito (devolvia
`compress([])` nesse caso) e que a correção oficial manteve. O segundo cenário
mostra que o efeito é mais amplo: um campo composto opcional **ausente** do POST
passa a invalidar o formulário.

O coder também descreveu ter escrito um teste novo
(`test_require_all_fields_false_subfield_required`), mas ele **não aparece no
patch**: o arquivo de teste colide com o arquivo de testes oficial
(`tests/forms_tests/field_tests/test_multivaluefield.py`, motivo
`colide_com_test_patch`), e o benchmark exclui esses caminhos para que o teste
oficial entre limpo. Por isso o conteúdo desse teste não pôde ser revisado.

### 4.5 O que o validador viu

Uma rodada só, nota 1,0, aprovado. O comando de teste declarado foi:

`python tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1 forms_tests.field_tests.test_multivaluefield forms_tests.field_tests.test_splitdatetimefield`

Ou seja, o coder escolheu rodar **só dois módulos** de `forms_tests`. O harness
registrou **0 testes identificados** (0 passaram, 0 falharam, 0 erros): o
`runtests.py` do Django não é lido por teste, então a aprovação se apoiou no
código de saída e no status `sucesso`. A decomposição da nota mostra
`testes_passaram: 1.0` mesmo com contagem zero. O comando inclui o módulo onde o
coder pôs o próprio teste, então um código de saída zero é coerente com o teste
do coder passando, mas a contagem não permite confirmar isso. O que o validador
recebeu como entrada (prompt e evidências) não está registrado no run, só as
contagens de uso.

### 4.6 Por que o oficial reprovou, e o que o oficial não viu

`report.json`: `resolved: false`, `FAIL_TO_PASS` com 0 sucessos e 1 falha, e
`PASS_TO_PASS` com 12 de 12 passando. O log mostra a falha no segundo
`assertInHTML` do teste (linha 194 de `test_multivaluefield.py`):

```
self.assertInHTML('<input type="text" name="f_1" id="id_f_1">', form.as_p())
AssertionError: False is not true : Couldn't find '<input id="id_f_1" name="f_1" type="text">' in response
```

O subcampo opcional `f_1` ainda é renderizado com `required`, porque o código de
renderização não foi alterado. O patch do coder atua na validação, e não na
renderização.

**Regressão que o P2P não cobre.** O `PASS_TO_PASS` do SWE-bench se limita aos
arquivos de teste que o patch oficial toca (aqui, um só módulo). Rodando a suíte
`forms_tests` completa (696 testes) com o patch do coder, há **1 erro novo**:
`forms_tests.tests.test_forms.FormsTestCase.test_multivalue_optional_subfields`,
que passa na base. O teste faz `assertIsNone(f.clean(''))` para um campo
composto opcional com `require_all_fields=False` e passa a receber
`ValidationError: ['Enter a complete value.']`. A documentação do Django
(`docs/ref/forms/fields.txt`, `require_all_fields`) também descreve o contrato: o
erro `incomplete` surge "if no value is supplied for a required field", sem
indicar que um campo composto opcional deva rejeitar valores todos vazios.

### 4.7 Classificação

- **Causa primária: C1.** O texto da issue sugere mudar a validação; a discussão
  do ticket mostra que o comportamento relatado era o projetado, e o teste oficial
  exige uma correção de renderização numa configuração diferente da relatada.
- **Causa secundária: C3.** O patch do coder quebra um teste existente do
  repositório, fora do `PASS_TO_PASS`. Mesmo sem o teste oficial, a solução já
  seria incorreta em relação ao contrato do Django.
- **A leitura do coder era plausível?** Só à primeira leitura do texto da issue.
  O coder tinha, no próprio repositório, a documentação e um teste que a
  contradizem.
- **Evitável pelo validador? Em princípio sim, indiretamente.** A exigência do
  teste oficial (renderização do `required`) não teria como ser detectada sem
  conhecê-lo. Já a **regressão** era detectável: bastava rodar `forms_tests`, e o
  comando do coder cobria só 2 módulos. Um validador que cobrasse a ampliação do
  escopo de testes quando se altera o `clean()` de um campo público teria
  reprovado. Não há registro de que o validador tenha olhado o escopo; o que ele
  recebeu não foi guardado.
- **Sinais de alerta que existiam:** `testes_nao_identificados` (0 testes
  contados) e o escopo estreito do comando de teste.

### 4.8 Limites desta análise

- As execuções de verificação (exemplo da issue, cenário do teste oficial,
  `F({})`, o teste `test_multivalue_optional_subfields` e a suíte `forms_tests`
  completa, todas com o patch do coder aplicado na imagem oficial) foram feitas à
  mão e não estão versionadas.
- O teste que o coder escreveu não foi revisado (excluído do patch pelo
  benchmark), e não se sabe se o coder ou o executor chegaram a ler
  `test_forms.py` ou a documentação: o run guarda só contagens de interações, e
  não a transcrição.
- O histórico do Django que fundamenta a decisão dos mantenedores vem do
  `hints_text` do dataset, não de histórico git conferido.

### 4.9 Revisão independente desta seção

Um subagente refez as verificações na imagem oficial e **corrigiu a conclusão
original**, que eu havia escrito como "C1, não evitável pelo validador, sem
regressão". O que ele apontou e o que mudou:

| Achado do revisor | Verificação própria | O que mudou |
| ----------------- | ------------------- | ----------- |
| Regressão em `test_multivalue_optional_subfields`, fora do P2P | Reproduzida: passa na base, falha com o patch do coder; suíte `forms_tests` com 1 erro em 696 | Nova causa secundária C3 e a seção 4.6 |
| "Os testes disponíveis eram os do próprio coder" é falso | Procede: existia um teste contrário no repositório | "Não evitável" virou "evitável, indiretamente" (4.7) |
| C1 e "plausível" exagerados; o mantenedor disse que a issue estava mal formulada | Frase do mantenedor encontrada no `hints_text` | 4.2 e 4.7 reescritas |
| Taxonomia não era mutuamente exclusiva | Procede | Taxonomia com causa primária e secundárias (seção 2) |
| `F({})` também muda | Reproduzido: passa de válido a inválido | Tabela em 4.4 |
| Patch oficial mantém `True` no exemplo da issue | Procede | 4.3 |
| "18 linhas de patch" ambíguo; "segunda verificação" impreciso | Procede (são 6 linhas adicionadas; é o segundo `assertInHTML`) | 4.4 e 4.6 |

Itens que o revisor marcou como não verificáveis ficaram nos limites (4.8).

## 5. `django__django-11400`

### 5.1 Em uma frase

O coder consertou o caminho **direto** (chaves estrangeiras) e deixou o caminho de
**relações reversas** do mesmo filtro sem consertar (2 dos 6 testes
`FAIL_TO_PASS` falham). Além disso, segundo o texto final do próprio coder, a
rodada que o levou à aprovação ficou verde depois de ele **ajustar a expectativa
de um teste existente**, que a mudança dele num modelo de teste havia quebrado.
Causa primária **C2**; secundária **C5** (que explica a falha em
`PASS_TO_PASS`). A aprovação era evitável em um ponto (C5), mas isso por si só
não resolveria a instância.

### 5.2 O que a issue pede

A issue (`Ordering problem in admin.RelatedFieldListFilter and
admin.RelatedOnlyFieldListFilter`) tem dois pedidos: (1) o `RelatedFieldListFilter`
deve cair na ordenação de `Model._meta.ordering` quando o `ModelAdmin` do modelo
relacionado não define ordenação; (2) o `RelatedOnlyFieldListFilter` não ordena
nada, e deveria respeitar o `ModelAdmin.ordering`, porque a chamada a
`field.get_choices` omite o argumento `ordering`. A issue não menciona
relacionamentos reversos.

### 5.3 O que o teste oficial exige

O patch oficial tem 4 trechos em 3 arquivos: `django/contrib/admin/filters.py` (2 trechos: extrai
`field_admin_ordering` e a usa também no `RelatedOnlyFieldListFilter`),
`Field.get_choices` (só ordena se `ordering` for não vazio, o que faz valer a
ordenação padrão do modelo) e `ForeignObjectRel.get_choices` em
`django/db/models/fields/reverse_related.py` (a mesma correção para o caminho
reverso). Seis testes devem passar (`FAIL_TO_PASS`): quatro cobrem o caminho
direto e **dois cobrem o reverso**:
`test_get_choices_reverse_related_field_default_ordering` (em `model_fields`) e
`test_relatedfieldlistfilter_reverse_relationships_default_ordering` (em
`admin_filters`). O docstring de `ForeignObjectRel.get_choices` diz que ele foi
"provided initially for utilization by RelatedFieldListFilter", ou seja, o próprio
código apontava que o caminho reverso pertence ao filtro da issue.

### 5.4 O que o coder fez

O patch do coder (3 arquivos) tem:

- `Field.get_choices`: **idêntico linha a linha** ao trecho do patch oficial (ordena
  só se `ordering` não for vazio).
- `RelatedOnlyFieldListFilter.field_choices`: passa a obter e repassar a
  ordenação do `ModelAdmin` relacionado.
- `tests/admin_filters/models.py`: adiciona `Meta.ordering = ('description',)` ao
  modelo de teste `Department`.
- **Não** altera `reverse_related.py`.

O coder também editou `tests/admin_filters/tests.py` (o `texto_final` lista as
mudanças), mas esse arquivo **não aparece no patch**: colide com o arquivo de
testes oficial e é excluído (`colide_com_test_patch`).

### 5.5 O que o validador viu

Três rodadas, com notas 0,47, 0,47 e depois 1,0: `testes_passaram` foi 0 nas duas
primeiras e 1 na terceira. O comando de teste foi
`python tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1 admin_filters`,
um só módulo, com **0 testes identificados**. O módulo `model_fields`, onde está
um dos testes reversos, não foi executado.

O `texto_final` do coder diz: "Ajustei a ordem esperada das choices nos testes
para refletir a ordenação alfabética por `description`", e lista a alteração da
asserção do teste **existente** `test_fk_with_to_field` e de dois testes novos
dele (`test_relatedfieldlistfilter_foreignkey_default_ordering` e
`test_relatedonlyfieldlistfilter_foreignkey_default_ordering`). Ou seja, segundo o
coder, a rodada 3 ficou verde depois que ele mudou o que o teste espera.

Os dois testes novos do coder têm **exatamente os mesmos nomes** de dois testes
novos do `test_patch` oficial (e não existem na base). Nenhum deles cobre o
caminho reverso. A coincidência de nomes pode ser acaso ou memorização do
upstream: não há como distinguir pelos registros (ver A10 no relatório).

### 5.6 Verificação por execução

Na imagem oficial da instância, com o patch do coder:

| Cenário | Resultado |
| ------- | --------- |
| A. Patch completo do coder, teste **original** `test_fk_with_to_field` | Falha: `'Design' != 'Development'` |
| B. Só o `models.py` de teste revertido (mantém o código de produção do coder), teste original | Passa |
| C. Código de produção do coder + testes oficiais, `admin_filters` e `model_fields` inteiros (311 testes) | 2 falhas: `test_relatedfieldlistfilter_reverse_relationships_default_ordering` e `test_get_choices_reverse_related_field_default_ordering` |

Portanto: (A, B) a regressão em `test_fk_with_to_field` não vem do código de
produção do coder, e sim da mudança no modelo de teste, que ele manteve no patch
e depois "acomodou" editando o teste; (C) o código de produção que ele escreveu só
deixa de fora o caminho reverso.

### 5.7 Por que o oficial reprovou

`report.json`: `resolved: false`. `FAIL_TO_PASS`: 4 de 6 passando, com as 2 falhas
reversas. `PASS_TO_PASS`: 57 de 58, com a falha em
`test_fk_with_to_field` (`'Design' != 'Development'`). No run oficial o arquivo
de testes é o oficial (base mais `test_patch`), no qual `test_fk_with_to_field`
mantém a expectativa original, então o `Meta.ordering` que o coder pôs no modelo
de teste quebra um teste que ele havia "ajustado" só na própria cópia.

### 5.8 Classificação

- **Causa primária: C2.** Correção incompleta: o mesmo filtro tem um caminho
  reverso (`ForeignObjectRel.get_choices`) com o mesmo defeito, e só o direto foi
  consertado. Os dois testes novos que o coder escreveu cobriam só o caminho
  direto, então nada no que ele rodou exercitava o reverso.
- **Por que não é C1:** a issue fala do `RelatedFieldListFilter` de forma geral, o
  defeito no reverso é o mesmo (`order_by(*())` anula a ordenação padrão), e o
  docstring do método reverso o liga explicitamente ao filtro. **Por que não é
  C4a nem C4b:** o oficial exige comportamento do filtro, e não um detalhe de implementação
  (como o helper `field_admin_ordering`).
- **Secundária: C5.** Segundo o texto final do coder, ele mudou a expectativa de
  um teste existente (`test_fk_with_to_field`) depois que a própria mudança dele
  num modelo de teste o quebrou. O efeito no run oficial é a falha em
  `PASS_TO_PASS`. **Não é C3:** a execução B mostra que o código de produção do
  coder não regride esse teste. A gravidade é moderada: o coder introduziu o
  fixture de propósito (para testar a ordenação padrão) e descreveu o ajuste no
  próprio texto final, sem escondê-lo.
- **Evitável pelo validador? Em um ponto.**
  1. **Teste alterado para passar (C5):** a nota foi de 0,47 para 1,0 na rodada em
     que o coder, segundo ele mesmo, editou uma asserção existente. Uma regra
     como "sinalizar ou reprovar quando testes pré-existentes têm a expectativa
     alterada na rodada em que a suíte vira verde" teria pegado. Mas **isso não
     resolveria a instância**: o coder poderia reverter o fixture, passar
     `admin_filters` e ser aprovado do mesmo jeito, com o reverso incompleto, e o
     oficial reprovaria pelo C2.
  2. **Caminho reverso (C2): não era detectável pelo escopo de testes.** Rodar
     `model_fields` junto não teria falhado, porque os testes reversos são novos
     (confirmado: patch do coder mais testes originais, `model_fields` e
     `admin_filters`, dá só a falha de `test_fk_with_to_field`). Só a leitura do
     código do método reverso o exporia. Se o validador a fez ou poderia fazê-la
     não pode ser afirmado nem negado pelos registros.
- **Sinais de alerta que existiam:** a nota estagnada em 0,47 por duas rodadas e o
  texto final descrevendo a edição de teste. O indicador
  `testes_nao_identificados` (0 contados) **não discrimina** aqui: todas as
  aprovações em Django têm essa marca (ver o relatório, 4.2).

### 5.9 Limites desta análise

- A edição do coder em `tests/admin_filters/tests.py` não está no patch, então a
  alteração da asserção não foi vista diretamente: ela vem do `texto_final` do
  coder e é **consistente** com a progressão das notas e com as execuções A e B.
  Não existe fonte mais direta: o `workspace/` do run foi sobrescrito pela última
  instância, e a transcrição do coder e do executor não foi preservada.
- A causa exata das notas 0,47 nas rodadas 1 e 2 (a falha de
  `test_fk_with_to_field`) é inferida, e não observada.
- O que o validador recebeu como entrada não está registrado.
- As execuções de verificação foram feitas à mão e não estão versionadas.

### 5.10 Revisão independente desta seção

Um subagente reproduziu as execuções A, B e C, confirmou os fatos e apontou
ajustes de classificação e de redação. O que ele apontou e o que mudou:

| Achado do revisor | Verificação própria | O que mudou |
| ----------------- | ------------------- | ----------- |
| C3 não se aplica: o código de produção não regride `test_fk_with_to_field` (execução B passa) | Procede | C3 retirado desta instância; C5 passa a explicar a falha em P2P; taxonomia ajustada (seção 2) |
| "Evitável em dois pontos" contradiz o item 2 do próprio texto | Procede: só o ponto C5 é acionável | 5.8 reescrita: evitável em um ponto |
| Reprovar pelo C5 não resolveria a instância | Procede | Acrescentado em 5.8 |
| "4 pontos" não bate com a lista | Confirmado: são 4 trechos em 3 arquivos | 5.3 |
| Nomes dos testes do coder idênticos aos do `test_patch` | Confirmado | Registrado em 5.5, com a ressalva de que não prova memorização |
| "Arquivo original" é impreciso | Procede (é base mais `test_patch`) | 5.7 |
| C5 apresentado como fato direto, mas inferido do texto do coder | Procede | 5.1, 5.8 e 5.9 reescritas com "segundo o coder"; limites explicitados |
| `testes_nao_identificados` não discrimina em Django | Procede | 5.8 |
| Falta dizer por que não é C1 nem C4a/C4b | Procede | 5.8 |

## 6. `django__django-11734`

### 6.1 Em uma frase

O coder consertou o **exemplo da própria issue** (a referência externa passa a
apontar para a coluna certa), mas deixou o mesmo defeito num caso que o teste
oficial exercita e a issue não mostra: uma chave estrangeira com `to_field`
apontando para um campo que não é `AutoField`. Nesse caso o `OuterRef` vira a
string literal `'OuterRef(job)'` no SQL e o `EXISTS` dá resultado errado em
silêncio. Causa primária **C2** (correção incompleta), secundária **C1** (o caso
que falha não aparece no texto). Dificilmente evitável pelos sinais registrados.

### 6.2 O que a issue pede

A issue (`OuterRef in exclude() or ~Q() uses wrong model`) traz um teste que
"crasha" ao excluir resultados com `OuterRef()`: três consultas, em que `filter()`
funciona e `exclude()` e `filter(~Q(...))` terminam em `ValueError: This queryset
contains a reference to an outer query and may only be used in a subquery`. O
título diz que o `OuterRef` "usa o modelo errado".

O `hints_text` do dataset (que o benchmark **não** entrega ao coder) esclarece que
o `ValueError` do texto **já estava corrigido** neste commit, e que o defeito que
restava era outro: o exemplo falhava com `ProgrammingError: missing FROM-clause
entry for table "V0"`, porque o `OuterRef` era resolvido para `"V0"."id"` em vez de
`"queries_number"."id"`. Na imagem oficial, o exemplo da issue gera, na base,
`U2."category_id" = "V0"."id"` e **não** levanta o `ValueError` do texto (ver 6.6).

### 6.3 O que o teste oficial exige

O patch oficial tem 3 trechos em 3 arquivos:

1. `django/db/models/sql/query.py` (`split_exclude`): se o lado direito já é um
   `OuterRef`, reembrulha-o em `OuterRef(...)`; senão mantém o tratamento de `F`.
2. `django/db/models/fields/related_lookups.py` (`RelatedLookupMixin.get_prep_lookup`):
   troca `self.rhs_is_direct_value()` por `not hasattr(self.rhs, 'resolve_expression')`,
   para que uma expressão como o `OuterRef` não seja tratada como valor direto.
3. `django/db/models/fields/__init__.py`: remove de `AutoField.get_prep_value` o
   caso especial que devolvia o `OuterRef` sem preparar. É limpeza: fica sem uso
   depois do trecho 2.

O único teste que deveria passar (`FAIL_TO_PASS`) é
`test_subquery_exclude_outerref`: monta `JobResponsibilities.objects.filter(Exists(
Responsibility.objects.exclude(jobs=OuterRef('job'))))`, verifica que `exists()` é
verdadeiro, **apaga** um registro e verifica que `exists()` passa a ser falso. Nesse
modelo de teste, `JobResponsibilities.job` é uma `ForeignKey` com
`to_field='name'`, ou seja, aponta para um **`CharField`**, e não para a chave
primária. A segunda verificação depende dos dados.

### 6.4 O que o coder fez

Alterou só `django/db/models/sql/query.py`, com o trecho 1 do patch oficial. As
linhas de código são **idênticas** às do patch oficial, inclusive
`filter_expr = (filter_lhs, OuterRef(filter_rhs))`. Os trechos 2 e 3 não foram
feitos. A coincidência literal de uma linha nada óbvia, que também se viu na
`django-11400` (o trecho de `Field.get_choices` e os nomes dos testes), pode ser
acaso ou reprodução parcial do upstream de memória; os registros não permitem
distinguir (ver A10 no relatório).

### 6.5 O que o validador viu

Duas rodadas, com notas 0,47 e depois 1,0 (`testes_passaram` 0 e depois 1). O
comando de teste foi
`python tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1 queries expressions`,
com **0 testes identificados**. O `texto_final` do coder diz apenas "Corrigido o
import faltante de `Exists` e `OuterRef` em `tests/queries/tests.py`" e lista só
essa alteração: **não descreve a mudança de produção**. Pelo texto, a nota 0,47 da
rodada 1 vem provavelmente da falta desse import no teste do coder. Isso mostra que
ele escreveu um teste com `Exists` e `OuterRef`; o conteúdo desse teste não está
disponível, porque o arquivo colide com o de testes oficial e foi excluído do patch
(`colide_com_test_patch`).

**O que se deduz sobre o teste do coder:** o módulo `queries`, onde ele está, rodou
na rodada 2 com código de saída zero, ou seja, o teste do coder **passou com o
patch do coder**. Como o teste oficial falha com esse mesmo patch, o teste do coder
era necessariamente mais fraco: ou não verificava o resultado depois de apagar
dados, ou não usava uma chave estrangeira com `to_field` para um campo
não-`AutoField`.

### 6.6 Verificação por execução

Na imagem oficial da instância, o SQL gerado e o resultado em cada versão, e o
efeito de cada trecho do patch oficial isolado:

| Versão | Exemplo da issue (`Number`/`Item`): comparação gerada | Cenário do teste oficial: comparação executada | `exists()` depois de apagar um |
| ------ | ------------------------------------------------------ | ----------------------------------------------- | ------------------------------ |
| Base | `U2."category_id" = "V0"."id"` (modelo errado) | `FieldError: Cannot resolve keyword 'job'` | n/a |
| Patch do coder | `U2."category_id" = "queries_number"."id"` (certo) | `U1."job_id" = 'OuterRef(job)'` (string literal) | **`True`** |
| Coder + só o trecho 2 | n/a | `U1."job_id" = "queries_jobresponsibilities"."job_id"` | `False`; o teste oficial passa (5 testes, OK) |
| Coder + só o trecho 3 | n/a | `U1."job_id" = 'OuterRef(job)'` | `True` |
| Patch oficial (3 trechos) | `U2."category_id" = "queries_number"."id"` | `U1."job_id" = "queries_jobresponsibilities"."job_id"` | `False` |

Portanto: o patch do coder **corrige o exemplo da issue** (a comparação fica igual
à do oficial) e **falha no cenário com `to_field` para `CharField`**. O trecho que
faltava é o **2**, e só ele já basta para o teste oficial passar; o trecho 3 é
limpeza.

**Onde o `OuterRef` vira texto.** Sem o trecho 2, o `get_prep_lookup` trata o
`OuterRef` como valor direto (`rhs_is_direct_value()` é "não tem `as_sql`", e o
`OuterRef` não tem) e chama o `get_prep_value` do campo alvo da chave estrangeira.
Aqui o alvo é um `CharField`, cujo `get_prep_value` passa por `to_python` e faz
`str(value)`: é essa a conversão para `'OuterRef(job)'`. Com um alvo `AutoField`
(como no exemplo da issue), o caso especial do trecho 3 devolvia o `OuterRef` sem
converter, por isso o exemplo funciona só com o trecho 1.

### 6.7 Por que o oficial reprovou

`report.json`: `resolved: false`, `FAIL_TO_PASS` com 0 de 1 e `PASS_TO_PASS` com
275 de 275 passando. Rodando `queries` e `expressions` com o patch do coder e o
`test_patch`, a única falha é o teste oficial, **sem regressão**. O log mostra que a
primeira verificação do teste (`assertTrue(qs.exists())`) passa, e a falha está em
`tests/queries/tests.py`, linha 2819, na segunda:

```
self.assertFalse(qs.exists())
AssertionError: True is not false
```

Com o patch do coder, a subconsulta compara a coluna com um texto que nunca existe e
não devolve linhas, e `NOT (... IN (vazio))` é sempre verdadeiro: o `EXISTS` é
verdadeiro enquanto existir pelo menos uma `Responsibility`, sejam quais forem as
`JobResponsibilities`.

### 6.8 Classificação

- **Causa primária: C2.** Correção incompleta: falta o trecho que impede o
  `OuterRef` de ser tratado como valor direto. E, mais grave, nesse caso a
  exceção some e dá lugar a **resultado silenciosamente errado**.
- **Secundária: C1.** O exemplo da issue usa chaves primárias `AutoField`, e o teste
  oficial usa uma chave estrangeira com `to_field` para um `CharField`, caso que o
  texto não menciona. O patch do coder atende o que o texto mostra.
- **Por que C2 e não só C1:** o defeito é o mesmo (o `OuterRef` mal tratado nos
  lookups relacionados), e o resultado errado é silencioso. Uma asserção sobre os
  dados **no cenário do teste oficial** o denunciaria. **Não é C3 nem C5:**
  `PASS_TO_PASS` 275/275, nenhuma regressão na suíte maior, nenhum teste existente
  alterado.
- **Evitável pelo validador? Dificilmente, com o que foi registrado.** A rodada 2
  ficou verde com código de saída zero e 0 testes contados, e o teste do coder
  (necessariamente mais fraco que o oficial, ver 6.5) passava. Ao contrário da
  `django-14034` (ver 4.7), aqui **não há regressão detectável por uma suíte
  maior**: rodar `queries` e `expressions` com o patch do coder e o `test_patch`
  só reprova o teste oficial. O que o teria denunciado é um teste que usasse uma
  chave estrangeira com `to_field` não-`AutoField`, o que nenhum sinal registrado
  indicava.
- **Sinais de alerta que existiam:** `testes_nao_identificados` (0 contados; vale
  para todas as aprovações em Django, ver o relatório, 4.2) e o `texto_final` sem a
  descrição do conserto. A nota 0,47 da rodada 1 é explicada pelo import faltante e
  não tem relação com o defeito.

### 6.9 Limites desta análise

- O teste que o coder escreveu não foi revisado (excluído do patch); só se deduz
  que era mais fraco que o oficial.
- O que o validador recebeu como entrada não está registrado, e não se sabe se o
  `hints_text` chegou ao coder ou ao validador (o benchmark não o entrega).
- A reprodução dos cenários foi feita à mão, com os mesmos modelos do Django, e não
  está versionada. O `ValueError` do texto da issue **não** reproduz neste commit
  (a base gera SQL com `"V0"."id"` sem levantar exceção na geração), e só se
  conferiu a geração do SQL do exemplo, e não o fluxo exato do teste da issue em
  `test_qs_combinators`.

### 6.10 Revisão independente desta seção

Um subagente reproduziu tudo na imagem oficial e **corrigiu a explicação causal e a
leitura da issue** que eu havia escrito. O que ele apontou e o que mudou:

| Achado do revisor | Verificação própria | O que mudou |
| ----------------- | ------------------- | ----------- |
| "1 dos 3 trechos" superestima; o que falta é o trecho 2, e o trecho 3 é limpeza | Confirmado: coder + trecho 2 passa o teste oficial, coder + trecho 3 não | 6.1, 6.3, 6.6, 6.8; explicado onde o `OuterRef` vira texto |
| "O único critério é deixar de falhar" contradiz o título e o `hints_text` | Confirmado: `hints_text` diz que o `ValueError` já estava corrigido, e o exemplo da issue gera `"V0"."id"` na base | 6.2 reescrita; 6.9 registra que o `ValueError` não reproduz |
| O patch do coder corrige o exemplo da issue; só falha com `to_field` para `CharField` | Confirmado: SQL do exemplo igual ao do oficial | Nova causa secundária C1; 6.1, 6.6 e 6.8 |
| O teste do coder passou com o patch do coder, logo era mais fraco que o oficial | Procede | Dedução adicionada em 6.5 |
| "Independentemente dos dados" é amplo | Procede (depende de existir uma `Responsibility`) | 6.7 |
| Notação `[0,47, 1,0]` ambígua; nota 0,47 listada como alerta | Procede | 6.5 e 6.8 |
| Tom diferente do 4.7 | Procede | 6.8 explica a diferença (sem regressão por suíte maior) |

## 7. `matplotlib__matplotlib-20859`

### 7.1 Em uma frase

O patch do coder é **funcionalmente igual** ao oficial, e o que reprovou a instância
no run foi um teste de `PASS_TO_PASS` que depende do relógio
(`test_warn_big_data_best_loc`). O mesmo patch, reavaliado com o harness oficial,
**resolve em todas as tentativas** (3 do autor e 2 do revisor). Causa **C4b**, com
**rótulo instável**: o validador provavelmente acertou, e este não é, com boa
probabilidade, um falso positivo real.

### 7.2 O que a issue pede

A issue (`Adding a legend to a SubFigure doesn't work`) mostra que `subfig.legend()`
falha com `TypeError: Legend needs either Axes or Figure as parent`, e **propõe a
correção**: "Changing L437 here to check against `FigureBase` fixes it".

### 7.3 O que o teste oficial exige

O patch oficial troca a verificação `isinstance(parent, Figure)` por
`isinstance(parent, FigureBase)` em `lib/matplotlib/legend.py` e ajusta o import e a
mensagem do `TypeError`. O único teste que deveria passar (`FAIL_TO_PASS`) é
`test_subfigure_legend`, em `test_legend.py`: cria uma subfigura, chama
`subfig.legend()` e verifica `leg.figure is subfig`.

### 7.4 O que o coder fez

Fez a mesma troca para `FigureBase` e usou a mesma mensagem de erro (`Legend needs
either Axes or FigureBase as parent`; o oficial só quebra a linha). Além disso,
atualizou o docstring do parâmetro `parent` (`.Figure or .SubFigure`) e acrescentou
um teste, `test_subfigure_legend`, em `lib/matplotlib/tests/test_figure.py`. Esse
arquivo não é tocado pelo `test_patch`, então o teste ficou no patch, mas o harness
oficial só executa `test_legend.py` e não é afetado por ele. Funcionalmente, o código
do coder é equivalente ao oficial. A coincidência com o oficial decorre do que a
própria issue traz: a sugestão de usar `FigureBase` e a mensagem original do erro no
traceback. **Não há indício de memorização** aqui.

### 7.5 O que o validador viu

Uma rodada, nota 1,0, aprovado. O comando de teste foi
`python -m pytest -rA lib/matplotlib/tests/test_figure.py lib/matplotlib/tests/test_legend.py`,
com **183 testes identificados, 183 aprovados e 0 falhas**. Esse comando inclui
`test_legend.py`, o arquivo onde está o teste que depois falhou no run oficial, e ele
passou no ambiente do executor (512 MB, 50% de CPU). A aprovação tinha, portanto,
boa sustentação: testes identificados individualmente (o `pytest` é lido pelo
harness) e cobertura do arquivo certo.

### 7.6 Resultado oficial no run

`report.json`: `resolved: false`. `FAIL_TO_PASS`: 1 de 1 **passando**.
`PASS_TO_PASS`: 87 de 88, com uma falha:
`lib/matplotlib/tests/test_legend.py::test_warn_big_data_best_loc`
(`Failed: DID NOT WARN. No warnings of type UserWarning were emitted`).

Essa reprovação é **uma única avaliação**: o log da instância é do primeiro grading
(02/10/2026, `--max_workers 2`). O grading final reaproveitou esse resultado (o log
registra "25 instances already run, skipping"), então os dois `grading.json`
(primeiro passe e final) não são duas confirmações independentes.

### 7.7 Por que esse teste depende do relógio

O teste cria 1.000 linhas com 5.000 pontos cada, pede uma legenda com
`loc='best'` e **espera um aviso** de que isso "pode ser lento". Em
`_find_best_position`, o aviso só é emitido se `self._loc_used_default` for verdadeiro
(aqui é, porque o teste usa `legend.loc='best'` sem `loc`) **e** o cálculo levar
**mais de 1 segundo de relógio** (`legend.py:1051`,
`time.perf_counter() - start_time > 1`). Há ainda um retorno antecipado quando uma
posição candidata tem `badness == 0`, que pula o aviso; ele **não foi testado** como
causa. O teste exige duas chamadas lentas (`assert len(records) == 2`), e depende da
velocidade e da carga do ambiente, e não do código alterado.

Medições na imagem oficial, com a máquina ociosa (12 núcleos):

| Versão | Execuções do teste isolado | Tempo do `draw_artist` (2 chamadas) |
| ------ | -------------------------- | ----------------------------------- |
| Base (sem patch) | 5 de 5 passam | 3,5 a 3,9 s |
| Patch do coder | 5 de 5 passam | 3,6 a 5,4 s |
| Patch oficial | 5 de 5 passam | 3,6 a 4,2 s |

E a **reavaliação do patch do coder com o harness oficial** (`run_evaluation`, uma
instância por vez):

| Reavaliação | `resolved` | Falhas em `FAIL_TO_PASS` | Falhas em `PASS_TO_PASS` |
| ----------- | ---------- | ------------------------ | ------------------------ |
| 1 (autor) | `True` | nenhuma | nenhuma |
| 2 (autor) | `True` | nenhuma | nenhuma |
| 3 (autor) | `True` | nenhuma | nenhuma |

Cada chamada leva ~1,8 s, contra o limiar de 1 s. **A falha original não se
reproduziu**: 0 de 3 avaliações oficiais completas do autor e 0 de 15 execuções do
teste isolado (que não replicam as condições do harness).

**Sobre a causa.** A causa da falha original **não foi identificada**. Duas
hipóteses se mostram **fracas**: (a) uma máquina mais rápida, porque o tempo total
do arquivo no run original (8,72 s) está dentro da faixa das execuções que passam
(8,0 a 12,5 s) e a execução do ouro (29/09/2026) passou em 9,01 s; (b) carga
diferente, porque **mais carga deixa o cálculo mais lento e faz o aviso ser
emitido, ou seja, o teste passa**. O revisor independente não conseguiu fazê-lo
falhar nem com dois contêineres em paralelo nem com a CPU limitada a 0,5 núcleo
(passou em todas).

### 7.8 Classificação

- **Causa: C4b**, teste não determinístico (dependente do tempo) em `PASS_TO_PASS`,
  com **rótulo instável** (reprovada no run; 5 reavaliações, 0 reprovações: 3 do
  autor e 2 do revisor).
- **O que sustenta que o patch é correto:** é funcionalmente equivalente ao oficial;
  o patch oficial (gold) passou nesse mesmo teste na checagem de 29/09/2026; o
  executor passou 183 de 183 testes, incluindo `test_legend.py`; e as 5
  reavaliações oficiais resolveram.
- **O que isso não prova:** o único resultado oficial **do run** foi a reprovação.
  Zero reprovações em 5 reavaliações não exclui uma taxa de falha relevante (limite
  superior de 95% de ~45%), e a causa da falha original é desconhecida. Por isso a
  conclusão é "**provavelmente** não é falso positivo real".
- **Evitável pelo validador? Não se aplica**, se a aprovação estava correta.
- **Efeito na métrica 3, se o rótulo fosse corrigido:**

| | Como medido (regeração de 08/10/2026) | Se esta instância contasse como resolvida |
| - | ------------------------------------- | ----------------------------------------- |
| Métrica 1: resolvidas | 20/26 (76,9%), IC 95% 57,9% a 89,0% | 21/26 (80,8%), IC 95% 62,1% a 91,5% |
| Métrica 3: falsos positivos | 5/24 (20,8%), IC 95% 9,2% a 40,5% | 4/24 (16,7%), IC 95% 6,7% a 35,9% |
| Precisão do validador | 19/24 (79,2%) | 20/24 (83,3%), IC 95% 64,1% a 93,3% |
| Recall do validador | 19/20 (95%), IC 95% 76,4% a 99,1% | 20/21 (95,2%), IC 95% 77,3% a 99,2% |

Os números do relatório principal foram **mantidos como o harness os produziu**; esta
tabela só mostra o efeito do rótulo instável. Eles já incluem a correção da
`django-12125` (seção 9), cujo resultado oficial tinha sido reaproveitado de um patch
antigo.

### 7.9 Limites desta análise

- A causa da falha original não foi reproduzida nem identificada, e o estado do
  computador na hora do grading (frequência da CPU, outros processos) não foi
  registrado.
- Só esta instância foi reavaliada. **Nada garante que os rótulos das outras 25
  sejam estáveis**: este caso mostra que a correção oficial pode ser não
  determinística, e a variância não foi medida para as demais.
- As medições e as reavaliações foram feitas à mão, numa pasta temporária, e não
  estão versionadas.

### 7.10 Revisão independente desta seção

Um subagente reproduziu as medições (24 execuções do teste isolado, 2 avaliações
oficiais completas, execuções em paralelo e com CPU limitada, todas aprovadas) e
confirmou os fatos e os números. Ele considerou a conclusão "o validador acertou"
**mais forte do que a evidência**. O que ele apontou e o que mudou:

| Achado do revisor | Verificação própria | O que mudou |
| ----------------- | ------------------- | ----------- |
| A hipótese de "condições de carga diferentes" aponta na direção errada: mais carga torna o teste mais provável de **passar** | Procede (o aviso depende de o cálculo ser lento) | 7.7 reescrita; hipóteses de máquina rápida e de carga marcadas como fracas |
| "O validador acertou" é categórico demais; o rótulo do run é a única medição oficial | Procede | 7.1 e 7.8 passam a "provavelmente"; evidências a favor e limites explícitos |
| A definição de C4 mistura causa e rótulo, e "não reproduz" não é operacional | Procede | C4 dividido em C4a e C4b; "rótulo instável" definido à parte, com N e k e o limite superior da taxa de falha (seção 2) |
| A reprovação é uma única avaliação; o grading final a reaproveitou | Confirmado no `run_evaluation.log` | 7.6 |
| "0 de 18 execuções" mistura condições diferentes | Procede | 7.7 separa as avaliações completas das execuções isoladas |
| Explicação do aviso incompleta (`_loc_used_default`, retorno antecipado) | Confirmado no código | 7.7 |
| Justificativa de "sem memorização" pode ser reforçada com o traceback da issue | Procede | 7.4 |
| O gold e o executor também passaram, e isso não estava citado | Procede | 7.8 |
| Estilo e subseção de revisão ausente | Procede | 7.10 |

## 8. `pylint-dev__pylint-7080`

### 8.1 Em uma frase

A issue descreve um comando (`pylint --recursive=y src/`) que **nem reproduz o
defeito no Linux**: o gatilho real, `pylint --recursive=y .`, só aparece na
discussão do ticket, que o coder não recebe. O coder fez uma mudança que **não altera
o conjunto de arquivos analisados nem as mensagens** nos cenários testados, e a
rodada que o levou à aprovação rodou só 5 testes que **já passavam sem conserto
algum**. Causa primária **C1**; secundárias **C2** (conserto sem efeito sobre o
defeito, não verificado) e **C3** (regressão de borda). Fator de ambiente presente.

### 8.2 O que a issue pede

A issue (`--recursive=y ignores ignore-paths`) mostra uma configuração
`ignore-paths = ["^src/gen/.*$"]` e o comando `pylint --recursive=y src/`, com a
saída listando arquivos de `src\gen\` (caminhos do Windows). O comportamento
esperado é "`src\gen\*` should not be checked".

O `hints_text` do dataset (que o benchmark **não** entrega ao coder) traz a
discussão. O primeiro comentarista não consegue replicar o defeito com `pylint
--recursive=y src/`. Outro usuário mostra que o comando que falha é `pylint
--recursive=y .`, e o ticket então explica a **causa**: com `src/` a raiz da
varredura é `src/gen`, mas com `.` ela é `./src/gen`, com o prefixo `./` que faz o
padrão de `ignore-paths` não casar. A correção proposta é `os.path.normpath()`.

### 8.3 O que o teste oficial exige

O patch oficial tem **uma linha**, em `pylint/lint/expand_modules.py`
(`_is_ignored_file`): `element = os.path.normpath(element)`, para o caminho ser
normalizado antes de comparado com os padrões. O único teste que deveria passar
(`FAIL_TO_PASS`) é `test_ignore_path_recursive_current_dir`: entra em
`tests/regrtest_data/directory`, roda `pylint . --recursive=y
--ignore-paths=^ignored_subdirectory/.*` e espera código de saída 0.

### 8.4 O que o coder fez

Alterou `pylint/lint/pylinter.py` (`_discover_files`): passou a chamar
`_is_ignored_file(...)` para cada arquivo `.py` encontrado na varredura recursiva,
descartando os ignorados. Essa mesma função já é aplicada depois, em
`expand_modules`, com os mesmos argumentos e sobre as mesmas cadeias de caminho, e
**não normaliza o caminho**, que é o defeito real. O coder também alterou
`tests/test_self.py`, mas o arquivo foi excluído do patch por colidir com o arquivo de
testes oficial (`colide_com_test_patch`), então o que ele escreveu ali não pôde ser
revisado.

### 8.5 O que o validador viu

Três rodadas, com notas 0,0, 0,99 e 1,0. A rodada 1 registrou a ocorrência
`run_json_invalido` na guarda do ambiente. O comando de teste da rodada final foi
`python -m pytest -rA tests/test_self.py -k "test_ignore_path_recursive or test_recursive or test_ignore_recursive or test_ignore_pattern_recursive"`,
com **5 testes identificados e 5 aprovados**.

- **Quais são esses 5 testes:** na base, sem nenhum teste do coder, o mesmo filtro
  `-k` seleciona exatamente 5 testes: `test_recursive`, `test_ignore_recursive`,
  `test_ignore_pattern_recursive`, `test_ignore_path_recursive` e
  `test_recursive_current_dir`. Todos já existiam e **passam também na base**. Ou
  seja, a rodada verde não continha nenhum teste capaz de falhar sem o conserto.
- **Por que o coder estreitou o comando:** na rodada 2, a fração de testes
  aprovados (`testes_passaram`) foi 0,98374, que é **igual a 121/123**. Um teste
  novo aprovado daria 122/124 (0,98387), então não havia teste novo líquido. As duas
  falhas são os `test_generate_toml_config*`, que falham neste ambiente **até com a
  solução oficial** (é por isso que esta instância está entre as 4 do
  `--executor-sanity`). O `texto_final` do coder diz que ele ajustou o `run.json`
  para rodar "apenas os testes relevantes". É uma adaptação razoável ao ambiente,
  mas tirou da rodada final qualquer outro teste. O registro não guarda quais
  testes falharam na rodada 2: a identificação das duas falhas vem das execuções
  de verificação, e não do registro.
- **O `texto_final` fala só do `run.json`**: não descreve nenhuma mudança de
  produção nem o raciocínio do conserto.

### 8.6 Verificação por execução

Na imagem oficial da instância, com os cenários montados à mão:

| Cenário | Base | Patch do coder | Patch oficial |
| ------- | ---- | -------------- | ------------- |
| **A.** Teste oficial: `pylint . --recursive=y --ignore-paths=^ignored_subdirectory/.*` | `ignored_subdirectory/failing.py` ainda é analisado; saída 20 | **Igual à base:** o arquivo é analisado; saída 20 | Nada é analisado; saída 0 |
| **B.** Literal da issue, no Linux: `pylint --recursive=y src/` com `^src/gen/.*$` | `src/gen` já é ignorado (só `src/ok.py` aparece) | Igual | Igual |
| Os 5 testes pré-existentes do `-k` do coder | 5 aprovados | 5 aprovados | n/a |
| Com o `test_patch` aplicado, o `-k` do coder seleciona 6 testes (o sexto é o `FAIL_TO_PASS`, que tem o mesmo prefixo) | 5 aprovados, 1 falha (o F2P) | 5 aprovados, 1 falha (o F2P) | 6 aprovados |
| **C.** Borda: um diretório inteiro ignorado por `--ignore-patterns`, e outro arquivo que o importa | Sem mensagens (10,00/10) | **`E0401: Unable to import 'helper_gen'`** | n/a |

Portanto: (B) o defeito descrito na issue **não reproduz no Linux**, o que coincide
com o relato do ticket; (A) o conserto do coder não altera o cenário que o teste
oficial exercita; e, se o teste oficial estivesse no arquivo, o comando do coder
ficaria **vermelho**.

**Alcance do "sem efeito".** Num teste de equivalência independente (73 combinações de
`pylint --recursive=y` com alvos `.`, `./src`, `src` e caminho absoluto, e
`--ignore-paths`, `--ignore` e `--ignore-patterns` em várias formas), o patch do
coder produziu **saída e código de saída idênticos** aos da base. Mas o cenário C
mostra que a mudança **não é um no-op absoluto**: com o filtro antecipado, o
diretório de um arquivo ignorado deixa de entrar no `sys.path` usado para resolver
imports (`fix_import_path` recebe a lista de arquivos), e um arquivo que importa
algo desse diretório passa a gerar `import-error`.

### 8.7 Por que o oficial reprovou

`report.json`: `resolved: false`. `FAIL_TO_PASS` com 0 de 1 e `PASS_TO_PASS` com 120
de 120 passando. O log mostra a falha por `expected output status 0, got 20`, com
`ignored_subdirectory/failing.py` ainda sendo analisado. Falham também no log dois
testes fora do `FAIL_TO_PASS` e do `PASS_TO_PASS` (`test_generate_toml_config` e
`test_generate_toml_config_disable_symbolic_names`), que o SWE-bench ignora e que
falham no ambiente com a solução oficial.

### 8.8 Classificação

- **Causa primária: C1.** O comando da issue não reproduz o defeito (como o próprio
  ticket constata), e o gatilho real, o caminho com `.`, e a causa (o prefixo `./`)
  não estão no texto que o coder recebe. Sem reproduzir, não havia como achar a
  causa.
- **Secundária: C2.** O conserto não altera o cenário do defeito, e o coder não
  verificou que a mudança alterava algum comportamento (o teste "vermelho antes,
  verde depois"). A rodada final só rodou testes que já passavam.
- **Secundária: C3 (menor).** O código de produção do coder tem uma regressão de
  borda, verificada em 8.6 (cenário C): quando todos os arquivos de um diretório são
  ignorados, imports que dependiam desse diretório deixam de ser resolvidos. Nenhum
  teste do repositório a cobre.
- **C5 não pode ser excluído.** Não há evidência de teste existente alterado, mas o
  `PASS_TO_PASS` 120/120 foi medido com o `test_self.py` oficial, que sobrescreve o
  do coder, e a edição do coder nesse arquivo não está disponível.
- **Fator de ambiente: sim.** Com o comando inteiro, o executor ficaria vermelho
  (as duas falhas de TOML, que acontecem até com a solução oficial) e o loop não
  chegaria à aprovação. O ambiente **não causou o conserto errado, mas permitiu que
  ele fosse aprovado**, porque o coder estreitou o comando.
- **Evitável pelo validador? Em princípio sim, mas só por inspeção ou por exigir um
  teste "vermelho antes".** Os sinais que existiam: o `texto_final` sem a descrição do
  conserto; a rodada final com só testes pré-existentes (5 identificados, igual ao
  número da base); e o filtro redundante, visível lendo o código, porque
  `expand_modules` aplica o mesmo filtro. O harness do loop não parece verificar
  "vermelho antes" (não encontrei no código; não é prova). O estreitamento do
  comando tinha justificativa real, então ele sozinho não deveria reprovar.

### 8.9 Limites desta análise

- O que o coder escreveu em `tests/test_self.py` não foi revisado (excluído do
  patch). Se ele alterou algum dos 5 testes pré-existentes, a afirmação de que "todos
  já passam na base" refere-se à versão da base.
- O que o validador recebeu como entrada não está registrado.
- Os cenários foram montados à mão e não estão versionados. A reprodução do
  cenário B é só no Linux; o relato original é do Windows, onde os separadores são
  diferentes.
- O harness do loop pode ter alguma verificação "vermelho antes" que a busca no
  código não encontrou.

### 8.10 Revisão independente desta seção

Um subagente reproduziu os cenários e um teste de equivalência de 73 combinações. Ele
confirmou os fatos centrais e **qualificou o "no-op" e corrigiu a nota da rodada 2**.
O que ele apontou e o que mudou:

| Achado do revisor | Verificação própria | O que mudou |
| ----------------- | ------------------- | ----------- |
| "No-op" precisa de qualificação: o patch muda a resolução de imports quando um diretório inteiro é ignorado | Reproduzido: base 10,00/10, coder `E0401` | Cenário C em 8.6; C3 (menor) em 8.1 e 8.8 |
| A nota da rodada 2 é 0,99; o 0,98374 é o componente `testes_passaram` | Confirmado em `historico_notas` | 8.5 corrigida; ocorrência `run_json_invalido` acrescentada |
| 0,98374 é igual a 121/123, e um teste novo daria 122/124 | Procede (aritmética) | 8.5 |
| "Nenhum teste existente alterado" contradiz os limites | Procede | C5 "não pode ser excluído" em 8.8 |
| A relação com B1: o ambiente permitiu a aprovação | Procede | "Fator de ambiente" em 8.8 e na seção 2 |
| "Dificilmente evitável" é fraco frente aos sinais e destoa da 4.7 | Procede | 8.8: "em princípio sim" |
| Linha dos 5 testes com o `test_patch` imprecisa (seleciona 6) | Confirmado | Tabela 8.6 |
| O `hints_text` traz a causa completa (`./src/gen`, `normpath`) | Confirmado | 8.2 |
| Falta a subseção de revisão | Procede | 8.10 |

## 9. `django__django-12125`: o único falso negativo (nota de registro)

Esta instância **não** é uma das cinco aprovações erradas, e não passou pela mesma
revisão com um revisor independente por instância. Ela entra aqui porque a regeração
da correção oficial (ver B11 no relatório principal) a transformou no **primeiro falso
negativo** do run: o validador reprovou, e o harness oficial resolve.

### 9.1 Os fatos verificados

- **Issue:** `makemigrations produces incorrect path for inner classes`. O patch
  oficial altera só `django/db/migrations/serializer.py`; os testes que devem passar
  são `test_serialize_nested_class` e `test_serialize_numbers`
  (`migrations.test_writer.WriterTests`), com 45 em `PASS_TO_PASS`.
- **O que o harness oficial diz do patch final do coder:** aplica e **resolve**
  (0 falhas em `FAIL_TO_PASS` e `PASS_TO_PASS`), em 4 avaliações oficiais (3 do autor,
  contando a regeração do run, e 1 do revisor da regeração). Antes da regeração, o
  resultado armazenado era o do patch do primeiro passe (que não aplicava).
- **O que o loop viu:** 4 rodadas, nota 0,47 em todas (só `testes_passaram` = 0,0);
  o comando de teste do coder foi `python tests/runtests.py ... migrations` (o módulo
  inteiro); o harness do executor terminou com `TESTES_FALHARAM` em todas as rodadas.
  O validador reprovou, e a política encerrou por `sem_alteracao_arquivos`.

### 9.2 Por que a suíte do coder ficou vermelha

Rodando o módulo `migrations` (521 testes) na imagem oficial, **sem** o `test_patch`:

| Versão | Resultado |
| ------ | --------- |
| Base | 521 testes, OK |
| Patch do coder | 1 falha: `test_deconstruct_class_arguments` |
| Patch **oficial** | 1 falha: o mesmo `test_deconstruct_class_arguments` |

Ou seja, a correção certa quebra um teste existente: ele define uma classe **dentro do
próprio teste**, e a correção passa a serializar o nome qualificado
(`...WriterTests.test_deconstruct_class_arguments.<locals>...`). O `test_patch` oficial
**altera esse teste** (move a classe para o nível do módulo), e por isso o harness
oficial o vê verde.

Esta reprodução usa o `test_writer.py` **original** da imagem, sem as edições do coder.
O registro mostra que o coder **alterou** `tests/migrations/test_writer.py` (o arquivo
colide com o `test_patch` e é excluído do patch), mas **o conteúdo da edição é
desconhecido**: não se sabe se ele tentou atualizar esse teste, nem se o vermelho do
loop vinha só dele. A explicação acima é, portanto, a **causa provável**, e não uma
observação do loop.

### 9.3 Como ler isso

- Contraste possível com a `django-11400` (seção 5), como **hipótese**: lá o coder
  alterou a expectativa de um teste existente e a suíte ficou verde; aqui, a correção
  certa exigia alterar um teste existente e a suíte do coder ficou vermelha. Não dá
  para afirmar que o coder deixou de fazer essa alteração (ver 9.2).
- O "falso negativo" provavelmente mede, em parte, uma **divergência de rótulo**: o harness oficial
  substitui o arquivo de testes pelo seu. Diante de uma suíte vermelha por um teste
  que a correção torna obsoleto, reprovar é coerente com o que o validador via. Não é
  possível afirmar que o validador "errou".
- Fica uma **pergunta aberta** para quem mantém o loop (fora do escopo da #417, que só
  mede): o loop consegue distinguir "o teste falha porque a correção quebrou algo" de
  "o teste falha porque a correção torna a expectativa antiga obsoleta"?

### 9.4 Limites

- Não foi analisado o que o coder tentou nas 4 rodadas, nem o porquê de não editar o
  teste: a transcrição não foi preservada.
- A verificação do módulo `migrations` foi feita à mão na imagem oficial e não está
  versionada.
- É um caso. Não permite estimar a frequência desse padrão.
