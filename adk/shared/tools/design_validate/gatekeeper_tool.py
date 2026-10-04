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
from shared.tools.design_filesystem import _sanitize_mermaid, read_file
 
 
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
    if format == "mmd":
        # O arquivo salvo já é gravado sem cercas (save_artifact). O conteúdo
        # recebido aqui, porém, costuma vir de uma leitura repassada como
        # Markdown (```mermaid ... ```); sem isto, essa embalagem reprova o
        # diagrama como UNKNOWN_DIAGRAM e consome os ciclos de correção.
        content = _sanitize_mermaid(content)
    result = ArtifactGatekeeper.check(content=content, format=format)
    return result.to_dict()


def validate_artifact_file(filename: str) -> dict:
    """
    Valida deterministicamente um diagrama .mmd JÁ SALVO, lendo-o do disco.

    Mesmas regras e mesmo resultado de validate_artifact, mas recebe só o
    nome do arquivo (ex.: "diagrama_HU-001_login.mmd" ou
    "DIAGRAMS/diagrama_HU-001_login.mmd") — não é preciso repetir o conteúdo.
    O resultado é VERDADE ABSOLUTA, como em validate_artifact.

    Args:
        filename: Nome do arquivo .mmd na pasta de diagramas.

    Returns:
        Os mesmos campos de validate_artifact (valid, error_type,
        error_message, line_number, suggested_fix). Se o arquivo não puder
        ser lido: valid=False, error_type="READ_ERROR".
    """
    lido = read_file(filename, caller="validator")
    if lido.get("status") != "ok":
        return {
            "valid": False,
            "error_type": "READ_ERROR",
            "error_message": lido.get("error", "Falha ao ler o arquivo."),
            "line_number": None,
            "suggested_fix": "Confirme o nome exato do arquivo na listagem da pasta de diagramas.",
        }
    return validate_artifact(lido.get("content", ""), "mmd")
