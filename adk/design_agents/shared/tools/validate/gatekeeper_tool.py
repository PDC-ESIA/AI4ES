"""
gatekeeper_tool.py
──────────────────
Adaptador: expõe ArtifactGatekeeper como FunctionTool do Google ADK.
 
Uso no agente:
    from shared.tools.validate.gatekeeper_tool import validate_artifact
    from google.adk.tools import FunctionTool
 
    tools=[FunctionTool(validate_artifact), ...]
"""
 
from __future__ import annotations
 
# Ajuste o import conforme a estrutura real do seu projeto
from .artifact_gatekeeper import ArtifactGatekeeper
 
 
def validate_artifact(content: str, format: str) -> dict:
    """
    Valida deterministicamente um artefato gerado pelo Agente Arquiteto.
 
    Executa regras de parsing e gramática sem nenhum julgamento do LLM.
    O resultado deve ser tratado como VERDADE ABSOLUTA pelo agente:
    se valid=False, o artefato ESTÁ errado — não há interpretação possível.
 
    Args:
        content: Texto bruto do artefato (.mmd ou .md).
        format:  Extensão declarada do artefato — "mmd" ou "md".
 
    Returns:
        dict com os campos:
            valid          (bool)  – True somente se o artefato passou em todas as regras.
            error_type     (str|None)  – Categoria do erro (ex: "INVALID_GRAMMAR").
            error_message  (str|None)  – Descrição humana do problema encontrado.
            line_number    (int|None)  – Linha aproximada do erro, quando detectável.
            suggested_fix  (str|None)  – Ação concreta para corrigir o artefato.
    """
    result = ArtifactGatekeeper.check(content=content, format=format)
    return result.to_dict()
 