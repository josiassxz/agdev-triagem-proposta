import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SKILL = RAIZ / ".claude" / "skills" / "triagem-proposta"
sys.path.insert(0, str(SKILL / "scripts"))
