## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação usa deque e acessa head_history[p-1] para responder consultas do tipo 2. Indexação em collections.deque não é O(1) — é O(k) no índice — logo consultas com p grande tornam-se custosas. Com p até N (até 10^6) e até 2·10^5 consultas, esse acesso pode levar a tempo de execução muito alto (TLE). A estratégia precisa fornecer acesso O(1) à posição requerida (por ex. mantendo uma lista/array indexável ou outra estrutura com acesso direto).

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: A solução mantém um histórico de até N tuplas (x,y) em memória. Para N = 10^6 isso pode consumir centenas de megabytes em Python (cada int/tuple tem overhead), o que pode ser problemático dependendo do limite de memória do juiz. Recomenda-se usar estruturas mais compactas (por ex. duas listas de inteiros, arrays do módulo array, ou representação compacta) ou approach que não armazene todos N pares quando desnecessário.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues testes automatizados (arquivos de teste ausentes). Isso impede verificação automática da correção e regressões. (Critérios CA-01/CA-02 são automatizáveis — testes deveriam ser incluídos.)

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Não há cases de teste no workspace. Recomendo incluir testes cobrindo: movimentos apenas horizontais/verticais, p = 1, p = N, muitos movimentos (> N), e combinações intercaladas de queries tipo 1 e 2 para validar histórico e comportamento de truncamento.

## Resumo
A lógica funcional está correta em termos de posição calculada (a ideia de que parte p corresponde à posição do head p-1 movimentos atrás ou ao deslocamento inicial está correta). Contudo, a implementação usa collections.deque e faz indexação head_history[p-1], que é O(p) por consulta em deque — isto provavelmente causa Time Limit Exceeded para entradas com p grandes e muitos queries. Além disso há risco de uso de memória elevado ao armazenar N pares como tuplas. Não foram entregues testes. Por conter um problema de complexidade que afeta diretamente a execução em limites do enunciado, a entrega fica BLOQUEADA até que a indexação seja feita em tempo O(1) (por exemplo, substituir deque por lista com índice controlado, usar arrays separados para x e y, ou outra estratégia com acesso direto).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação usa deque e acessa head_history[p-1] para responder consultas do tipo 2. Indexação em collections.deque não é O(1) — é O(k) no índice — logo consultas com p grande tornam-se custosas. Com p até N (até 10^6) e até 2·10^5 consultas, esse acesso pode levar a tempo de execução muito alto (TLE). A estratégia precisa fornecer acesso O(1) à posição requerida (por ex. mantendo uma lista/array indexável ou outra estrutura com acesso direto).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "A solução mantém um histórico de até N tuplas (x,y) em memória. Para N = 10^6 isso pode consumir centenas de megabytes em Python (cada int/tuple tem overhead), o que pode ser problemático dependendo do limite de memória do juiz. Recomenda-se usar estruturas mais compactas (por ex. duas listas de inteiros, arrays do módulo array, ou representação compacta) ou approach que não armazene todos N pares quando desnecessário.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados (arquivos de teste ausentes). Isso impede verificação automática da correção e regressões. (Critérios CA-01/CA-02 são automatizáveis — testes deveriam ser incluídos.)",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Não há cases de teste no workspace. Recomendo incluir testes cobrindo: movimentos apenas horizontais/verticais, p = 1, p = N, muitos movimentos (> N), e combinações intercaladas de queries tipo 1 e 2 para validar histórico e comportamento de truncamento.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```