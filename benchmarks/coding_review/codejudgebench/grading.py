"""Avaliação de um par: o veredito do reviewer bate com o rótulo do dataset?

Nada é executado aqui. Os autores do CodeJudgeBench já rodaram os testes
ocultos: `pos_response` passa e `neg_response` falha. O reviewer avalia cada
resposta separadamente (modo pontual) e a escolha é derivada dos dois vereditos:

| pos       | neg       | desfecho      |
|-----------|-----------|---------------|
| APROVADO  | BLOQUEADO | ``correct``   |
| BLOQUEADO | APROVADO  | ``wrong``     |
| APROVADO  | APROVADO  | ``tie_approve`` (não distinguiu; aprovou código errado) |
| BLOQUEADO | BLOQUEADO | ``tie_block``   (não distinguiu; bloqueou código certo) |

Desfechos que ficam FORA da acurácia, cada um por um motivo diferente:
- ``operational``: a chamada falhou (cota, rede, timeout) — defeito do ambiente;
- ``no_code``: a resposta do dataset não tinha código — defeito do dado;
- ``invalid``: o reviewer respondeu sem status reconhecível — defeito do
  reviewer, medido pela taxa de resposta inválida, não pela acurácia.

As funções recebem os dicionários persistidos em `progress.jsonl` (não os
objetos do runner), para que o grading possa ser refeito offline.
"""

from __future__ import annotations

OUTCOMES_DECIDIDOS = ("correct", "wrong")
OUTCOMES_EMPATE = ("tie_approve", "tie_block")
OUTCOMES_AVALIAVEIS = OUTCOMES_DECIDIDOS + OUTCOMES_EMPATE
OUTCOMES_EXCLUIDOS = ("operational", "no_code", "invalid")

# Precedência quando as duas respostas falham por motivos diferentes: o defeito
# do ambiente mascara os demais (a resposta não chegou a ser julgada).
_PRECEDENCIA = ("operational", "no_code", "invalid")


def grade_pair(pos: dict, neg: dict) -> str:
    """Desfecho do par a partir dos resultados serializados de pos e neg.

    Cada dicionário precisa de ``outcome_kind`` (ok | invalid | operational |
    no_code) e ``verdict`` (pass | fail | absent).
    """
    tipos = {pos["outcome_kind"], neg["outcome_kind"]}
    for tipo in _PRECEDENCIA:
        if tipo in tipos:
            return tipo

    aprovou_pos = pos["verdict"] == "pass"
    aprovou_neg = neg["verdict"] == "pass"
    if aprovou_pos and not aprovou_neg:
        return "correct"
    if aprovou_neg and not aprovou_pos:
        return "wrong"
    return "tie_approve" if aprovou_pos else "tie_block"
