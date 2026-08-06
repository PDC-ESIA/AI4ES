# Lições transversais — core

> Escopo: `core`. **Nasce vazio, de propósito** (relatório §10.1, §12.4).
>
> Este arquivo é o destino de lições que se aplicam a MAIS DE UMA stack — não é onde a
> destilação escreve por padrão. O destino default de uma lição nova é sempre
> `stacks/<stack>/lessons.md`; ela só sobe pra cá quando o **mesmo padrão de falha** é
> observado, de forma independente, em **duas stacks diferentes** (critério de promoção
> falsificável, dispensa julgamento subjetivo do curador — relatório §12.4).
>
> A escrita aqui é feita pelo Estágio 3 (destilação `ExecutionReport → lição`), que **ainda
> não foi implementado** nesta issue — é a Frente 2/trabalho futuro descrito no relatório.
> Até lá, este arquivo permanece vazio e o `cr_feedforward` o carrega normalmente (lista
> vazia não quebra a montagem do pack).
>
> Formato do item, quando a promoção acontecer (ver `knowledge/README.md`):
>
> ```yaml
> trigger:       <error_code do harness ou padrão de falha>
> granularidade: estrategia
> corpo:         <instrução acionável, válida para as N stacks onde foi observada>
> evidencia:     <task_id>.report.json de cada stack onde o padrão apareceu
> escopo:        core
> status:        ativo
> proveniencia:  <stacks de origem> / <runs ou PRs que promoveram o item>
> ```

<!-- Nenhum item ainda. Ver nota acima sobre o critério de promoção. -->
