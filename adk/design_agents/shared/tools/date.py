from datetime import datetime

def current_date() -> str:
    """ 
    Retorna a data atual no formato YYYY-MM-DD
    
    Returns:
        str: data atual
    """
    return str(datetime.now().date())