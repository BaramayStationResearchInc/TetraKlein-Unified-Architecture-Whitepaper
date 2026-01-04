from pathlib import Path
import os

# Resolve repo root relative to this file
REPO_ROOT = Path(__file__).resolve().parent.parent

LOG_ROOT = Path(
    os.environ.get(
        "TK_LOG_DIR",
        REPO_ROOT / "logs" / "LATEST"
    )
)

LOG_ROOT.mkdir(parents=True, exist_ok=True)
