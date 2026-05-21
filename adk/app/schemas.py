from pydantic import BaseModel, Field
from typing import Dict

class VowelCountRequest(BaseModel):
    text: str = Field(..., description="Texto a ser analisado")

class VowelCountResponse(BaseModel):
    total_vowels: int = Field(..., description="Total de vogais identificadas no texto")
    vowel_counts: Dict[str, int] = Field(..., description="Contagem individual das vogais a, e, i, o, u")
