import json
from pathlib import Path

_TAX = json.loads((Path(__file__).resolve().parent.parent / "schemas" / "taxonomy.json").read_text())

VERSION: str = _TAX["version"]
CATEGORIES: list[str] = _TAX["categories"]
SKILL_AXES: list[str] = _TAX["skill_axes"]
FLAGS: list[str] = _TAX["flags"]
CHECKLIST: list[dict] = _TAX["checklist"]
CHECKLIST_IDS: list[str] = [c["id"] for c in CHECKLIST]
N_DIFFICULTY = 10  # levels 1..10
N_SKILL_LEVELS = 11  # levels 0..10
