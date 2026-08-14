"""Testes do parser do formato de saída do ReasoningBank.

O parser é o ponto do desenho que troca `output_schema` por markdown, e a razão
é o modo de falha nº 2 do pipeline: sob GitHub Copilot o `response_format` é
descartado por `litellm.drop_params`, o modelo nunca é obrigado a emitir JSON e
a validação Pydantic derruba a run depois do fato.

O contrato destes testes é, portanto: **o parser degrada, nunca levanta**. Toda
entrada malformada devolve menos itens — jamais uma exceção.
"""

import pytest

from shared.memory.extract import _MAX_ITENS, parse_memory_items

BEM_FORMADO = """
# Memory Item 1
## Title Declarar toda dependência importada no manifesto
## Description Import sem pacote declarado quebra o build.
## Content Todo símbolo importado precisa da dependência correspondente no
manifesto da stack. O nome do pacote nem sempre é igual ao nome do import.

# Memory Item 2
## Title Conferir a porta declarada no manifesto de execução
## Description O healthcheck usa a porta do manifesto, não a do processo.
## Content Em produtos-serviço a porta declarada deve bater com a porta em que
o comando de execução faz a aplicação escutar.
"""


def test_extrai_todos_os_campos_do_contrato():
    itens = parse_memory_items(BEM_FORMADO)

    assert len(itens) == 2
    assert itens[0]["title"] == "Declarar toda dependência importada no manifesto"
    assert itens[0]["description"] == "Import sem pacote declarado quebra o build."
    # O conteúdo multilinha é reunido numa string só.
    assert "manifesto da stack" in itens[0]["content"]
    assert "nome do import" in itens[0]["content"]


def test_respeita_o_teto_de_tres_itens_do_reasoning_bank():
    """O prompt pede "at most 3"; o modelo pode ignorar, o parser não pode."""
    entrada = "\n".join(
        f"# Memory Item {n}\n## Title Titulo {n}\n"
        f"## Description Desc {n}\n## Content {'x' * 60}"
        for n in range(1, 8)
    )

    assert len(parse_memory_items(entrada)) == _MAX_ITENS


def test_aceita_saida_embrulhada_em_cerca_de_codigo():
    """O próprio prompt mostra o formato dentro de ```, e o modelo copia isso."""
    itens = parse_memory_items("```markdown\n" + BEM_FORMADO + "\n```")

    assert len(itens) == 2


def test_aceita_valor_na_linha_seguinte_ao_cabecalho():
    entrada = """
# Memory Item 1
## Title
Configurar o diretório de dados antes do primeiro acesso
## Description
Caminho relativo de banco exige que a pasta exista.
## Content
Quando o banco usa caminho relativo, o diretório precisa ser criado no build.
"""
    itens = parse_memory_items(entrada)

    assert len(itens) == 1
    assert itens[0]["title"] == "Configurar o diretório de dados antes do primeiro acesso"
    assert itens[0]["description"].startswith("Caminho relativo")


def test_item_sem_titulo_e_descartado():
    """Sem título não há id estável, e sem id estável o dedup não funciona."""
    entrada = """
# Memory Item 1
## Description Sem titulo nenhum.
## Content Conteudo qualquer suficientemente longo para passar de qualquer piso.

# Memory Item 2
## Title Este tem titulo
## Description E descricao.
## Content E conteudo suficientemente longo para nao ser considerado truncado.
"""
    itens = parse_memory_items(entrada)

    assert len(itens) == 1
    assert itens[0]["title"] == "Este tem titulo"


def test_numeracao_e_nivel_de_cabecalho_nao_sao_semanticos():
    """Modelos variam entre '#'/'##' e entre numerar ou não. Nada disso importa."""
    entrada = """
## Memory Item
### Title Um titulo qualquer
### Description Uma descricao.
### Content Um conteudo suficientemente longo para o judge nao rejeitar depois.
"""
    itens = parse_memory_items(entrada)

    assert len(itens) == 1
    assert itens[0]["title"] == "Um titulo qualquer"


@pytest.mark.parametrize(
    "entrada",
    [
        "",
        "   \n\n  ",
        "Desculpe, não consegui analisar a trajetória.",
        "# Memory Item 1\n(o modelo parou aqui)",
    ],
    ids=["vazio", "so-espacos", "prosa-sem-formato", "cabecalho-sem-campos"],
)
def test_entrada_inutilizavel_devolve_lista_vazia_sem_levantar(entrada):
    """O contrato central: degradar para vazio, nunca explodir."""
    assert parse_memory_items(entrada) == []
