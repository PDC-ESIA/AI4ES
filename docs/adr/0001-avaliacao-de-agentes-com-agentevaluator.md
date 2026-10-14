# ADR 0001 — Avaliação de agentes com o módulo de avaliação do ADK

- **Status:** proposto
- **Data:** 2026-09-28, reescrito em 2026-10-13
- **Origem:** PR #419
- **Onde está:** `adk/tests/eval/`. O [README](../../adk/tests/eval/README.md) explica como usar, e as
  [notas](../../adk/tests/eval/NOTAS.md) trazem o que foi medido para chegar a esta decisão.

## Contexto

Nossos testes automatizados não usam LLM: onde haveria um agente, entra uma simulação. Isso
garante que o código ao redor funciona (as ferramentas, as validações, a montagem das
respostas), mas não diz nada sobre o agente em si: se ele usa as ferramentas certas, na ordem
certa, e chega ao resultado esperado. Hoje, uma mudança de prompt, de modelo ou de ferramenta
pode piorar um agente sem que nenhum teste perceba. A piora só aparece quando alguém roda o
pipeline e lê o que saiu.

Avaliar o agente de verdade tem um preço. Cada caso chama o LLM, leva minutos e consome cota, e
o mesmo agente pode responder diferente em duas execuções. O ADK, framework em que os agentes
são escritos, já traz um módulo de avaliação que roda a partir do pytest.

## Decisão

Vamos usar o módulo de avaliação que já vem com o ADK, em vez de construir o nosso. Cada agente
ganha alguns casos. Um caso tem a entrada, o que o agente encontra no disco e o resultado
esperado. A avaliação roda o agente de verdade, com LLM, e compara o que ele fez e respondeu com
o esperado. Como isso consome LLM e é lento, a suíte só roda quando alguém pede, fora dos testes
do dia a dia. E um caso só passa se o resultado final estiver certo: vimos que um agente pode
seguir os passos certos e ainda assim entregar a resposta errada.

## Alternativas consideradas

- **Construir um framework de avaliação próprio**, com executor de casos, métricas e juiz
  escritos por nós. Daria controle total sobre o formato dos casos e dos relatórios, mas
  reimplementaria o que o ADK já faz: rodar o agente com uma sessão preparada, registrar as
  ferramentas que ele chamou e as que lhe foram oferecidas, comparar respostas e usar um LLM
  como juiz. Também teria de acompanhar sozinho cada mudança do ADK. Onde o módulo do ADK não
  basta, ele aceita métricas escritas por nós, e foi o que fizemos.
- **Usar uma plataforma externa de avaliação**, como LangSmith, Langfuse ou a avaliação do
  Vertex AI. Elas oferecem painéis, histórico e comparação entre versões, que o ADK não tem.
  Em troca, exigem integrar e operar um serviço fora do projeto (no Vertex AI, uma conta do
  Google Cloud) e enviar para fora as execuções dos agentes. Um levantamento recente dessas
  ferramentas (Yehudai et al., versão de 2026) também observa que boa parte do que elas oferecem para
  avaliar agentes ainda está em fase inicial. Vale rever se o projeto passar a precisar de
  acompanhamento contínuo.
- **Avaliar pela interface web do ADK (Dev UI) ou pela linha de comando (`adk eval`)**, em vez
  do pytest. As duas usam o mesmo motor, mas a interface grava a conversa sem o estado inicial
  da sessão, do qual vários agentes do pipeline dependem, e só avalia o agente principal de cada
  app. Nenhuma das duas deixa conferir, depois de cada execução, o que o agente deixou no disco.
  A interface ficou como forma de rascunhar casos a partir de sessões reais.
- **Ter um LLM como juiz como critério principal.** Nesse modelo, um segundo LLM lê a resposta e
  diz se ela está certa. É flexível, mas multiplica as chamadas de cada caso e pode dar notas
  diferentes para a mesma resposta. Além disso, por padrão o juiz seria o mesmo modelo avaliado,
  que tende a favorecer as próprias respostas (Zheng et al., 2023). Ficou como verificação
  opcional, num caso só. Os outros comparam com resultados que não dependem de opinião.

## Consequências

- Uma piora de agente passa a ter onde aparecer, mas só quando alguém roda a suíte. Nenhum
  processo automático a executa, e o README diz quando rodar.
- Cada caso novo aumenta o custo de uma rodada. O custo medido está no README.
- O mesmo agente pode responder diferente de uma execução para outra. Cada caso roda mais de uma
  vez e precisa passar em todas, então essa variação aparece como falha, em vez de sumir numa
  média. Falha intermitente é informação sobre o agente: vai para uma issue do agente, e o caso
  não é afrouxado.
- Os casos dependem do que está no disco antes da execução. Se mudar o formato dos arquivos que
  os agentes trocam entre si, esses arquivos de partida mudam junto.
- O módulo do ADK tem limites: não enxerga o estado da sessão e lê de forma incompleta as
  chamadas que pausam o pipeline à espera de uma pessoa. Onde isso importa, o próprio teste
  confere o resultado, e as métricas próprias completam a leitura. O detalhe está nas notas.
- As métricas próprias se apoiam numa peça interna do ADK, então uma atualização do ADK pode
  exigir ajuste. Depois de atualizar, rode a suíte.

## Referências

- Yehudai, A. et al. *A Survey on Evaluation of LLM-based Agents.* arXiv:2503.16416, v2
  (abril de 2026). Os frameworks de avaliação e o aviso sobre a maturidade deles estão na §6.
- Zheng, L. et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023,
  Datasets and Benchmarks.
