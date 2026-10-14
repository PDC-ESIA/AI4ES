## Status: BLOQUEADO

## Issues

- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação está logicamente incorreta. O código ordena os arrays de cortes em ordem crescente e calcula apenas duas estratégias (todas horizontais antes de verticais e vice‑versa), retornando o mínimo entre elas. Isso falha para muitos casos porque a ordem ótima de cortes pode exigir intercalar cortes horizontais e verticais — a solução correta é a estratégia gulosa clássica: ordenar ambos os arrays em ordem decrescente e, em uma única passagem, sempre aplicar o corte de maior custo restante multiplicado pelo número atual de segmentos da outra direção, atualizando os contadores de segmentos à medida que aplica um corte. O código atual produz resultados divergentes do esperado (ex.: o caso de falha informado no enunciado permanece incorreto). Recomenda-se substituir a lógica por:
  - ordenar horizontalCut e verticalCut em ordem decrescente (sem mutar o input original),  
  - iterar consumindo o maior custo entre as duas listas, acumulando cost * (n_segundos_da outra direção), e incrementando o contador de segmentos da direção do corte escolhido.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há testes/unit tests entregues no workspace. Os critérios de aceite exigem correção para casos conhecidos (CA-02) e para toda entrada válida (CA-01). Deve ser adicionada uma suíte de testes que inclua pelo menos: os exemplos do enunciado, o caso de falha previamente reportado e casos de borda (m=1 e/ou n=1).

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: O código usa list.sort() in-place em horizontalCut e verticalCut, mutando os arrays de entrada. Isso pode surpreender quem chama a função. Recomenda-se trabalhar sobre cópias (por exemplo, usar sorted(...)) para evitar efeitos colaterais.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Casos de borda não são explicitamente considerados nem testados: m=1 ou n=1 (arrays de cortes vazios), entradas com cortes todos iguais, e limites superiores (m,n até 20). Adicionar testes para esses cenários para garantir comportamento correto e cobertura determinística.

## Resumo

A entrega contém apenas o arquivo solution.py conforme esperado, mas apresenta um bug lógico que torna a solução incorreta: ela não implementa a estratégia gulosa correta (intercalar cortes por custo decrescente) e portanto retorna resultados errados para entradas como a relatada no enunciado. Não há testes para validar correções nem cobertura dos casos de borda. Por esse motivo a task fica BLOQUEADA até que o algoritmo seja corrigido (implementar a fusão gulosa com ordenação decrescente) e sejam adicionados testes representativos (incluindo o caso de falha informado).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação está logicamente incorreta. O código ordena os arrays de cortes em ordem crescente e calcula apenas duas estratégias (todas horizontais antes de verticais e vice‑versa), retornando o mínimo entre elas. Isso falha para muitos casos porque a ordem ótima de cortes pode exigir intercalar cortes horizontais e verticais — a solução correta é a estratégia gulosa clássica: ordenar ambos os arrays em ordem decrescente e, em uma única passagem, sempre aplicar o corte de maior custo restante multiplicado pelo número atual de segmentos da outra direção, atualizando os contadores de segmentos à medida que aplica um corte. O código atual produz resultados divergentes do esperado (ex.: o caso de falha informado no enunciado permanece incorreto). Recomenda-se substituir a lógica por: ordenar horizontalCut e verticalCut em ordem decrescente (sem mutar o input original), iterar consumindo o maior custo entre as duas listas, acumulando cost * (n_segundos_da outra direção), e incrementando o contador de segmentos da direção do corte escolhido.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não há testes/unit tests entregues no workspace. Os critérios de aceite exigem correção para casos conhecidos (CA-02) e para toda entrada válida (CA-01). Deve ser adicionada uma suíte de testes que inclua pelo menos: os exemplos do enunciado, o caso de falha previamente reportado e casos de borda (m=1 e/ou n=1).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "O código usa list.sort() in-place em horizontalCut e verticalCut, mutando os arrays de entrada. Isso pode surpreender quem chama a função. Recomenda-se trabalhar sobre cópias (por exemplo, usar sorted(...)) para evitar efeitos colaterais.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Casos de borda não são explicitamente considerados nem testados: m=1 ou n=1 (arrays de cortes vazios), entradas com cortes todos iguais, e limites superiores (m,n até 20). Adicionar testes para esses cenários para garantir comportamento correto e cobertura determinística.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```