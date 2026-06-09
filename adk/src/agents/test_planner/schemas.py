from pydantic import BaseModel, Field


class TestCase(BaseModel):
    requirement_id: str = Field(description="ID do requisito associado (ex.: REQ-1)")
    test_name: str = Field(description="Nome do teste (ex.: test_login_valido)")
    input_description: str = Field(description="Entrada / pré-condição do teste")
    expected_output: str = Field(description="Saída / comportamento esperado")


class TestPlanOutput(BaseModel):
    test_cases: list[TestCase]
