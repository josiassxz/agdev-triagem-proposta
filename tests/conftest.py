"""Configuração do pytest: torna os módulos da skill importáveis nos testes.

Os scripts ficam em .claude/skills/triagem-proposta/scripts/ e não são um pacote
instalado; por isso a pasta é colocada no sys.path para `from regras import ...`.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SKILL = RAIZ / ".claude" / "skills" / "triagem-proposta"
sys.path.insert(0, str(SKILL / "scripts"))
