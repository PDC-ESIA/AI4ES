"""Pacote do Executor do workflow coding_review.

O objeto do agente vive em ``executor.agent`` (submódulo). Importe-o via
``from .executor.agent import agent`` para evitar sombrear o submódulo ``agent``
com o objeto (o que quebraria ``importlib.reload`` do módulo nos testes).
"""
