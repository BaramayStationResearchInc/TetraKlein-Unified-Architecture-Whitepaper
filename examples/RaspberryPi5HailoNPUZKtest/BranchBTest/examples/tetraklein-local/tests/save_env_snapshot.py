import json
import platform
import subprocess
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
# Helpers
# ---------------------------------------------------------------------

def cmd_out(cmd: str) -> str | None:
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except Exception:
        return None

# ---------------------------------------------------------------------
# Capability Detection: CUDA (optional)
# ---------------------------------------------------------------------

cuda = None
try:
    import cupy as cp  # type: ignore

    gpu0 = cp.cuda.runtime.getDeviceProperties(0)
    cuda = {
        "available": True,
        "runtime_version": int(cp.cuda.runtime.runtimeGetVersion()),
        "gpu_name": gpu0.get("name", b"").decode(errors="replace"),
        "driver": cmd_out("nvidia-smi --query-gpu=driver_version --format=csv,noheader"),
    }
except Exception as e:
    cuda = {
        "available": False,
        "error": f"{type(e).__name__}: {e}",
    }

# ---------------------------------------------------------------------
# Capability Detection: Hailo (optional)
# ---------------------------------------------------------------------

hailo = None
try:
    from hailo_platform import Device  # type: ignore

    devices = Device.scan()
    hailo = {
        "available": True,
        "device_count": len(devices),
        "devices": [str(d) for d in devices],
        "hailortcli_identify": cmd_out("hailortcli fw-control identify"),
    }
except Exception as e:
    hailo = {
        "available": False,
        "error": f"{type(e).__name__}: {e}",
    }

# ---------------------------------------------------------------------
# Environment Snapshot
# ---------------------------------------------------------------------

snapshot = {
    "timestamp": datetime.now(UTC).isoformat(),
    "system": platform.platform(),
    "machine": platform.machine(),
    "python": platform.python_version(),
    "cuda": cuda,
    "hailo": hailo,
}

out_path = LOG_DIR / "env_snapshot.json"
with open(out_path, "w") as f:
    json.dump(snapshot, f, indent=2)

print(f"[ OK ] Environment snapshot written to {out_path}")
