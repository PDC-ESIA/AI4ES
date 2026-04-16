import subprocess
import json
from pathlib import Path
import logging
import sys
from datetime import datetime, timezone



async def _gerar_doubt_artifact(id_artefato: str, motivo: str) -> str:
    """
    Gera o arquivo Doubt_Artifact.md e retorna o caminho do arquivo criado.
    O nó é pausado — a execução só retoma após intervenção humana.
    """
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    doubt_dir = TESTS_DIR.parent / "doubt_artifacts"
    doubt_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"Doubt_Artifact_{id_artefato}_{timestamp}.md"
    caminho = doubt_dir / nome_arquivo

    conteudo = f"""# Doubt_Artifact — Requirements Analyst Agent

  **ID do Artefato:** {id_artefato}
    **Data/Hora:** {timestamp}
    **Agente:** requirements_analyst_agent
    **Status:** BLOQUEADO — aguardando intervenção humana
    **Contexto lido:** {context_file_name} 

    ---

    **Trecho do contexto:** "...{citation}..."

     **Dúvida:** [DESCRICAO_CLARA_DA_INCERTEZA]

     **Sugestão do Agente:** [Opcional: O que o agente propõe como padrão]

    ---
    **Resolução:** _(preencher na revisão humana)_
        - **Responsável:** [ PREENCHER ]
        - **Data:** [ PREENCHER ]
        - **Ação tomada:** [ PREENCHER ]
       
"""

    caminho.write_text(conteudo, encoding="utf-8")
    return str(caminho)


