## Status: APROVADO

## Issues
[]

## Resumo
A solução em solution.py implementa a estratégia gulosa correta: ordena os cortes horizontais e verticais em ordem decrescente e aplica sempre o próximo corte de maior custo multiplicado pelo número atual de segmentos na direção ortogonal. A implementação trata corretamente casos limites (listas vazias quando m=1 ou n=1), mantém contadores de peças consistentes e resolve a falha observada no exemplo fornecido. Não há problemas de arquitetura relevantes nem riscos de segurança; não foram exigidos testes no escopo desta entrega. Portanto o código está tecnicamente correto e pode prosseguir no pipeline.

```json
{
  "status": "APROVADO",
  "issues": []
}
```