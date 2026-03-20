import logging
import requests

from datetime import datetime
from google.adk.tools import ToolContext
from pydantic import BaseModel, Field, field_validator

class Weather(BaseModel):
    city: str = Field(
        default="",
        description="Cidade"
    )
    temperature: str = Field(
        default="",
        description="Temperatura",
        max_length=1000
    )
    description: str = Field(
        default="",
        description="Descrição do tempo",
        max_length=1000
    )


def tool_get_weather(params: Weather, tool_context: ToolContext) -> dict:
    """
    Obtem o tempo em uma cidade:
    
    Args:
        params (Weather): Parâmetros com avaliação da sessão e memórias
        tool_context (ToolContext): Contexto da ferramenta
        
    Returns:
        dict: Resultado da operação
    """
# --- Validate/Convert Input ---
    if isinstance(params, dict):
        try:
            params_validados = Weather.model_validate(params)
        except Exception as e:
            logging.error(f"Erro de validação Pydantic: {e}")
            return {"status": "Erro", "error": f"Dados de entrada inválidos: {e}", "result": None}
    elif isinstance(params, Weather):
        params_validados = params

    tool_context.state["cities"] = params_validados.city
    return Weather(city=params_validados.city, temperature="25°C", description="Sunny")
