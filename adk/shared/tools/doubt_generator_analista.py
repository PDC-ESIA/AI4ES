import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List

def gerar_doubt_artifact(
    id_duvida: str,
    id_artefato_afetado: str,
    trecho_contexto: str,
    duvida_descricao: str,
    motivo: str,
    impacto: str,
    bloqueante: bool = False,
    sugestao: Optional[str] = None,
    sessao: str = "001",
    contexto_geral: str = "Documentação de Requisitos",
    caminho_base: str = "docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/"
) -> str:
    """
    Gera um arquivo versionado Doubt_Artifact_<ID>_<TS>.md baseado no template oficial do Agente Analista.
    
    Args:
        id_duvida: Identificador sequencial da dúvida (ex: D-001).
        id_artefato_afetado: ID do artefato impactado (ex: HU-001, RF-002).
        trecho_contexto: Citação literal ou referência do documento original.
        duvida_descricao: Descrição clara da incerteza.
        motivo: Por que a dúvida surgiu.
        impacto: O que o agente assumiu como padrão caso não seja resolvida.
        bloqueante: Se a dúvida impede a continuação do fluxo.
        sugestao: Proposta do agente para resolução.
        sessao: Número da sessão/rodada atual.
        contexto_geral: Nome do arquivo ou resumo do contexto lido.
        caminho_base: Diretório onde o arquivo Doubt_Artifact_<ID>_<TS>.md será salvo.
        
    Returns:
        Caminho completo do arquivo gerado.
    """
    diretorio = Path(caminho_base)
    diretorio.mkdir(parents=True, exist_ok=True)
    data_hora_obj = datetime.now()
    data_hora = data_hora_obj.strftime("%d-%m-%Y %H:%M")
    timestamp = data_hora_obj.strftime("%Y%m%d_%H%M%S_%f")
    id_duvida_seguro = "".join(c for c in id_duvida if c.isalnum() or c == "-").strip("-")
    if not id_duvida_seguro:
        id_duvida_seguro = "D-UNKNOWN"
    arquivo_path = diretorio / f"Doubt_Artifact_{id_duvida_seguro}_{timestamp}.md"

    cabecalho = f"""# Doubt_Artifact — Registro de Dúvida do Agente

> Este arquivo registra uma incerteza, ambiguidade ou informação faltante
> identificada pelo agente durante a leitura do contexto e geração de requisitos.
> Deve ser revisado por um humano antes da próxima rodada de refinamento.

---

## Metadados da Sessão

| Campo              | Valor                                       |
|--------------------|---------------------------------------------|
| Sessão / Rodada    | {sessao}                          |
| Data               | {data_hora}                          |
| Contexto lido      | {contexto_geral}                 |
| Artefatos gerados  | [Pendente] |

---

## Dúvida Registrada

"""

    # Formata a seção de dúvida D-NNN
    status_bloqueante = "Sim" if bloqueante else "Não"
    secao_duvida = f"""### {id_duvida}

- **Artefato afetado:** [{id_artefato_afetado}]
- **Trecho do contexto:** "{trecho_contexto}"
- **Dúvida:** {duvida_descricao}
- **Motivo da dúvida**: {motivo}
- **Impacto se não resolvida:** {impacto}
- **Bloqueante:** {status_bloqueante}
- **Status:** Aberta
- **Sugestão do Agente:** {sugestao if sugestao else "N/A"}
- **Resposta:** _(preencher na revisão humana)_

---
"""

    with open(arquivo_path, "w", encoding="utf-8") as f:
        f.write(cabecalho + secao_duvida)
        
    return str(arquivo_path.absolute())
