# Lições destiladas — stack `python-fastapi`

> Escopo: `stack:python-fastapi`. Destino DEFAULT de toda lição nova extraída de execuções
> reais (relatório §12.4) — diferente de `pitfalls.md` no mesmo diretório, que é semente
> manual e estável. **Nasce vazio, de propósito** (§10.1).
>
> Política de escrita, quando o Estágio 3 (destilação `ExecutionReport → lição`) for
> implementado — **ainda não está**, é trabalho futuro fora desta issue:
> - só escrever após `state['validation'].status == "aprovado"` (validação executável, não
>   opinião do LLM);
> - update delta-incremental — nunca reescrita completa do arquivo (evita o *context
>   collapse* que o ACE documenta);
> - dedup e deprecação ativas;
> - **curadoria humana obrigatória antes de qualquer escrita** — o GovMem mediu que, de 133
>   candidatos reais de agentes de código, nenhum foi considerado seguro para promoção
>   automática;
> - chave de indexação primária: `stages[].error_code` do harness (granularidade
>   acionada-por-evento, que o CODESKILL mede como superior à granularidade de tarefa).
>
> Formato do item (ver `knowledge/README.md` para o campo completo):
>
> ```yaml
> trigger:       <error_code do harness, ex. APP_NAO_INICIALIZOU>
> granularidade: evento
> corpo:         <instrução acionável específica desta stack>
> evidencia:     <task_id>.report.json que originou a lição
> escopo:        stack:python-fastapi
> status:        ativo
> proveniencia:  <run/PR de origem>
> ```
>
> Quando o MESMO padrão (mesmo `trigger`) for observado, de forma independente, em uma
> segunda stack, ele é candidato a promoção para `core/lessons.md` (critério D8).

<!-- Nenhum item ainda. Estágio 3 (destilação) não implementado nesta issue. -->
