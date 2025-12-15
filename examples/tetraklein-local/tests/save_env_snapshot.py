import json
import platform
import subprocess
import cupy as cp
import os
from datetime import datetime, UTC
from pathlib import Path

# ---------------------------------------------------------------------
# Canonical Log Directory (same contract as tests)
# ---------------------------------------------------------------------

LOG_DIR = Path(
    os.environ.get(
        "TK_LOG_DIR",
        Path(__file__).resolve().parent.parent / "logs" / "LATEST"
    )
)

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Environment Snapshot
# ---------------------------------------------------------------------

snapshot = {
    "timestamp": datetime.now(UTC).isoformat(),
    "system": platform.platform(),
    "python": platform.python_version(),
    "cuda_runtime": cp.cuda.runtime.runtimeGetVersion(),
    "gpu": cp.cuda.runtime.getDeviceProperties(0)["name"].decode(),
    "driver": subprocess.getoutput(
        "nvidia-smi --query-gpu=driver_version --format=csv,noheader"
    ),
}

with open(LOG_DIR / "env_snapshot.json", "w") as f:
    json.dump(snapshot, f, indent=2)

print(f"[ OK ] Environment snapshot written to {LOG_DIR / 'env_snapshot.json'}")
