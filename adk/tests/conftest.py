"""Configura o PYTHONPATH para os testes.

Garante que o pacote local ``shared`` (e demais módulos do ADK) possam ser
importados tanto quando os testes são executados de dentro do diretório ``adk``
quanto a partir da raiz do monorepo.
"""

from __future__ import annotations

import sys
from pathlib import Path


ADK_ROOT = Path(__file__).resolve().parents[1]

if str(ADK_ROOT) not in sys.path:
    sys.path.insert(0, str(ADK_ROOT))
