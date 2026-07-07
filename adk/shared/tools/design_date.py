from datetime import datetime

def current_date() -> str:
    """Retorna a data atual no formato ISO YYYY-MM-DD.

    Use para timestamping de operações do IO Agent, logs de
    observabilidade ou versionamento de artefatos. Não inclui hora —
    apenas a data calendárica do servidor.

    Returns:
        str no formato "YYYY-MM-DD" (ex: "2026-05-17").
    """
    return str(datetime.now().date())