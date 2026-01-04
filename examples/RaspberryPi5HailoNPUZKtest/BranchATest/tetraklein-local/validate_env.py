#!/usr/bin/env python3
"""
TetraKlein Environment Validation
---------------------------------
Purpose:
  Verify that all declared environment constraints exist,
  are internally consistent, and remain within approved bounds.

Classification:
  INTERNAL — R&D VALIDATION ONLY

Policy:
  - Read-only
  - No auto-correction
  - Fail fast on violation
"""

import os
import sys
from pathlib import Path

ENV_DIR = Path("env")

REQUIRED_FILES = [
    "system.env",
    "compute.env",
    "crypto.env",
    "xr.env",
    "safety.env",
    "paths.env",
    "versions.lock",
]

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def die(msg):
    print(f"[ENV FAIL] {msg}")
    sys.exit(1)

def ok(msg):
    print(f"[ OK ] {msg}")

def parse_env_file(path):
    data = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                die(f"Malformed line in {path.name}: {line}")
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data

# ---------------------------------------------------------------------
# File Presence Check
# ---------------------------------------------------------------------

def check_files():
    if not ENV_DIR.exists():
        die("env/ directory does not exist")

    for fname in REQUIRED_FILES:
        path = ENV_DIR / fname
        if not path.exists():
            die(f"Missing required file: env/{fname}")
        ok(f"Found env/{fname}")

# ---------------------------------------------------------------------
# Semantic Validation
# ---------------------------------------------------------------------

def validate_system(env):
    if env.get("ARCH") != "x86_64":
        die("Unsupported architecture")

def validate_compute(env):
    if float(env.get("MAX_GPU_UTILIZATION", "1.0")) > 0.95:
        die("GPU utilization exceeds safe bound")

    if int(env.get("MAX_GPU_TEMP_C", "999")) > 85:
        die("GPU temperature limit too high")

def validate_crypto(env):
    if int(env.get("TRACE_DEGREE_MAX", "99")) > 4:
        die("Trace degree exceeds STARK-safe bounds")

    if int(env.get("FRI_QUERY_MAX", "999")) > 128:
        die("FRI query count exceeds approved ceiling")

def validate_xr(env):
    max_latency = int(env.get("MAX_LATENCY_MS", "0"))
    if max_latency <= 0 or max_latency > 500:
        die("XR latency budget invalid")

def validate_safety(env):
    if env.get("DETERMINISM_REQUIRED") != "true":
        die("Determinism must be enforced")

    if env.get("UNBOUNDED_STATE") == "true":
        die("Unbounded state explicitly forbidden")

def validate_paths(env):
    for k in ["LOG_DIR", "ARTIFACT_DIR", "CACHE_DIR"]:
        if k not in env:
            die(f"Missing path variable: {k}")
        if env[k].startswith("/"):
            die(f"Absolute paths forbidden: {k}")

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    print("\n=== TetraKlein Environment Validation ===\n")

    check_files()

    system = parse_env_file(ENV_DIR / "system.env")
    compute = parse_env_file(ENV_DIR / "compute.env")
    crypto  = parse_env_file(ENV_DIR / "crypto.env")
    xr      = parse_env_file(ENV_DIR / "xr.env")
    safety  = parse_env_file(ENV_DIR / "safety.env")
    paths   = parse_env_file(ENV_DIR / "paths.env")

    validate_system(system);  ok("system.env valid")
    validate_compute(compute); ok("compute.env valid")
    validate_crypto(crypto);  ok("crypto.env valid")
    validate_xr(xr);          ok("xr.env valid")
    validate_safety(safety);  ok("safety.env valid")
    validate_paths(paths);    ok("paths.env valid")

    print("\n[PASS] Environment contract satisfied")
    print("No violations detected\n")

if __name__ == "__main__":
    main()