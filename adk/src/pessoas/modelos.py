from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

class PessoaBase(BaseModel):
    """Schema base para dados de pessoa."""
    nome: str = Field(..., example="Maria Silva", description="Nome completo da pessoa")
    email: EmailStr = Field(..., example="maria@teste.com", description="E-mail da pessoa")
    data_nascimento: date = Field(..., example="1990-10-01", description="Data de nascimento no formato YYYY-MM-DD")

class PessoaCriacao(PessoaBase):
    """Schema para criação de pessoa (entrada)."""
    pass

class PessoaResposta(PessoaBase):
    """Schema para resposta ao listar ou cadastrar (inclui ID)."""
    id: int = Field(..., example=1, description="Identificador gerado para a pessoa")
