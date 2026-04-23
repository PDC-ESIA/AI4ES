from pydantic import BaseModel, Field

class TextRequest(BaseModel):
    text: str = Field(..., description="Texto de entrada para contagem de vogais")

class VowelCountResponse(BaseModel):
    vowel_count: int = Field(..., description="Número de vogais encontradas no texto")
