import os
from pathlib import Path

HOME = Path(os.environ.get("SLM_TAMER_HOME", Path.home() / ".slm-tamer"))
MODELS_DIR = HOME / "models"
ADAPTERS_DIR = HOME / "adapters"
DATASETS_DIR = HOME / "datasets"
EVALS_DIR = HOME / "evals"
LOGS_DIR = HOME / "logs"
TOOLS_DIR = HOME / "tools"
LLAMA_CPP_HOME = Path(
    os.environ.get("LLAMA_CPP_HOME", Path.home() / "tools" / "llama.cpp")
)
CONVERT_PYTHON = Path(
    os.environ.get("SLM_TAMER_CONVERT_PYTHON", TOOLS_DIR / "convert-venv" / "bin" / "python")
)
DB_PATH = HOME / "slm-tamer.db"


def ensure_dirs() -> None:
    for p in (HOME, MODELS_DIR, ADAPTERS_DIR, DATASETS_DIR, EVALS_DIR, LOGS_DIR, TOOLS_DIR):
        p.mkdir(parents=True, exist_ok=True)
