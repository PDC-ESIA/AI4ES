"""Pacote do Reviewer do workflow coding_review.

O objeto do agente vive em ``reviewer.agent`` (submódulo). Importe-o via
``from .reviewer.agent import agent`` para evitar sombrear o submódulo ``agent``
com o objeto (o que quebraria ``importlib.reload`` do módulo nos testes).
"""
