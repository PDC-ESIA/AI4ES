"""Testes unitários para os agentes TACO — schemas, imports e configuração.

Valida que todos os agentes TACO:
- Importam corretamente
- Possuem output_schema configurado (quando aplicável)
- Schemas são instanciáveis com dados mínimos válidos
- O orchestrator de jornada compõe os sub-agentes corretos
"""

import pytest


# ---------------------------------------------------------------------------
# Imports e configuração básica dos agentes
# ---------------------------------------------------------------------------

class TestTacoGabaritoAgent:
    def test_import_and_config(self):
        from src.agents.taco_gabarito.agent import root_agent
        from src.agents.taco_gabarito.schemas import GabaritoOutput

        assert root_agent.name == "taco_gabarito"
        assert root_agent.output_schema is GabaritoOutput

    def test_schema_instanciavel(self):
        from src.agents.taco_gabarito.schemas import (
            GabaritoOutput,
            SolucaoVariacao,
            ValidacaoExemplo,
        )

        exemplo = ValidacaoExemplo(
            stdin="1 2 3", esperado="6", obtido="6", passou=True
        )
        variacao = SolucaoVariacao(
            rotulo_variacao="iterativa",
            resumo_abordagem="Usa for explícito.",
            codigo="def solve(line): return sum(int(x) for x in line.split())",
            conceitos_exercitados=["split", "sum", "generator expression"],
            validacao_exemplos=[exemplo],
        )
        output = GabaritoOutput(solucoes=[variacao])

        assert len(output.solucoes) == 1
        assert output.solucoes[0].rotulo_variacao == "iterativa"
        assert output.solucoes[0].validacao_exemplos[0].passou is True


class TestTacoReviewerAgent:
    def test_import_and_config(self):
        from src.agents.taco_reviewer.agent import root_agent
        from src.agents.taco_reviewer.schemas import TacoReviewOutput

        assert root_agent.name == "taco_reviewer"
        assert root_agent.output_schema is TacoReviewOutput

    def test_schema_instanciavel(self):
        from src.agents.taco_reviewer.schemas import (
            Problema,
            Rubrica,
            TacoReviewOutput,
        )

        problema = Problema(
            tipo="estilo",
            gravidade="baixa",
            descricao="Uso de range(len()) desnecessário.",
            linha_aproximada=4,
        )
        rubrica = Rubrica(corretude=100, estilo=70, eficiencia=80)
        output = TacoReviewOutput(
            pontos_fortes=["Código funcional"],
            problemas_encontrados=[problema],
            sugestoes_de_melhoria=["Pesquise iteração direta sobre listas."],
            avaliacao_geral=rubrica,
        )

        assert output.avaliacao_geral.corretude == 100
        assert output.problemas_encontrados[0].linha_aproximada == 4

    def test_problema_sem_linha(self):
        from src.agents.taco_reviewer.schemas import Problema

        p = Problema(tipo="lógica", gravidade="alta", descricao="Bug.")
        assert p.linha_aproximada is None


class TestTacoResearchAgent:
    def test_import_and_config(self):
        from src.agents.taco_research.agent import root_agent
        from src.agents.taco_research.schemas import MapaConceitual

        assert root_agent.name == "taco_research"
        assert root_agent.output_schema is MapaConceitual

    def test_schema_instanciavel(self):
        from src.agents.taco_research.schemas import Conceito, MapaConceitual

        c1 = Conceito(
            ordem=1,
            nome="variáveis",
            descricao="Fundamento básico.",
            pre_requisitos=[],
        )
        c2 = Conceito(
            ordem=2,
            nome="listas",
            descricao="Coleções ordenadas.",
            pre_requisitos=["variáveis"],
        )
        mapa = MapaConceitual(
            escopo="Fundamentos Python",
            nivel_alvo="iniciante",
            conceitos=[c1, c2],
        )

        assert len(mapa.conceitos) == 2
        assert mapa.conceitos[1].pre_requisitos == ["variáveis"]


class TestTacoArchitectAgent:
    def test_import_and_config(self):
        from src.agents.taco_architect.agent import root_agent
        from src.agents.taco_architect.schemas import JornadaOutput

        assert root_agent.name == "taco_architect"
        assert root_agent.output_schema is JornadaOutput

    def test_schema_instanciavel(self):
        from src.agents.taco_architect.schemas import (
            Exemplo,
            Exercicio,
            JornadaOutput,
        )

        ex = Exemplo(stdin="5", stdout="25")
        exercicio = Exercicio(
            ordem=1,
            titulo="Quadrado de um número",
            enunciado="## Objetivo\nCalcule o quadrado.",
            dificuldade="easy",
            tags=["aritmética"],
            bibliotecas_permitidas=[],
            formato_entrada="Um inteiro N",
            formato_saida="N ao quadrado",
            exemplos=[ex, Exemplo(stdin="3", stdout="9")],
            objetivo_pedagogico="Operações aritméticas básicas.",
            depende_de=[],
        )
        jornada = JornadaOutput(
            titulo_jornada="Matemática básica",
            racional_pedagogico="Progressão de operações simples.",
            exercicios=[exercicio],
        )

        assert jornada.exercicios[0].depende_de == []
        assert len(jornada.exercicios[0].exemplos) == 2

    def test_exercicio_com_dependencias(self):
        from src.agents.taco_architect.schemas import Exemplo, Exercicio

        e = Exercicio(
            ordem=3,
            titulo="Compor funções",
            enunciado="Use as funções dos exercícios anteriores.",
            dificuldade="medium",
            tags=["composição"],
            bibliotecas_permitidas=[],
            formato_entrada="Texto",
            formato_saida="Texto",
            exemplos=[Exemplo(stdin="a", stdout="b")],
            objetivo_pedagogico="Composição de funções.",
            depende_de=[1, 2],
        )

        assert e.depende_de == [1, 2]


class TestTacoJourneyOrchestrator:
    def test_import_and_composition(self):
        from src.agents.taco_journey_orchestrator.agent import root_agent

        assert root_agent.name == "taco_journey_orchestrator"
        sub_names = [a.name for a in root_agent.sub_agents]
        assert sub_names == ["taco_research", "taco_architect"]

    def test_sub_agents_have_output_schema(self):
        from src.agents.taco_journey_orchestrator.agent import root_agent

        for sub in root_agent.sub_agents:
            assert sub.output_schema is not None, (
                f"Sub-agent {sub.name} deve ter output_schema definido"
            )
