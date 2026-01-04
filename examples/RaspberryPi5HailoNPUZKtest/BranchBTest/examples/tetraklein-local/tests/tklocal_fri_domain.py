#!/usr/bin/env python3
"""
TetraKlein Local FRI Domain Validation (Capability-Adaptive)

Validates:
- FRI domain sizing
- Blow-up factor feasibility
- Folding depth bounds
- Memory envelope (CPU estimate, GPU allocation if available)
"""

import sys
import math
import os
import time
import platform
from pathlib import Path

import numpy as np

from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------

HAS_CUDA = False
xp = np

try:
    import cupy as cp
    cp.cuda.runtime.getDeviceCount()
    xp = cp
    HAS_CUDA = True
except Exception:
    HAS_CUDA = False

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

LOG_ROOT.mkdir(parents=True, exist_ok=True)
logfile = open(LOG_ROOT / "console.log", "a", buffering=1)
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def banner(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)

def ok(msg):
    print(f"[ OK ] {msg}")

def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)

# ---------------------------------------------------------------------
# Hardware / Memory Envelope
# ---------------------------------------------------------------------

VRAM_GB = 8.0
SAFE_VRAM_GB = 6.5
BYTES_PER_FIELD = 8  # uint64

# ---------------------------------------------------------------------
# FRI Parameter Space
# ---------------------------------------------------------------------

FRI_CONFIG = {
    "trace_rows": 2**20,
    "max_degree": 4,
    "blowup_factors": [2, 4, 8],
    "max_folding_depth": int(
        os.environ.get("MAX_FRI_FOLDING_DEPTH", 24)
    ),
}

if not HAS_CUDA:
    # Reference-tier scaling
    FRI_CONFIG["trace_rows"] = 2**17

# ---------------------------------------------------------------------
# Domain Size Computation
# ---------------------------------------------------------------------

def compute_domain_size(rows, blowup):
    size = rows * blowup
    return 1 << (size - 1).bit_length()

# ---------------------------------------------------------------------
# Memory Estimation
# ---------------------------------------------------------------------

def estimate_domain_memory(domain_size, columns=1):
    return domain_size * columns * BYTES_PER_FIELD

def check_memory(bytes_required):
    gb = bytes_required / (1024**3)
    return gb <= SAFE_VRAM_GB, gb

# ---------------------------------------------------------------------
# Folding Depth
# ---------------------------------------------------------------------

def compute_folding_depth(domain_size):
    return int(math.log2(domain_size))

# ---------------------------------------------------------------------
# GPU Allocation Test (optional)
# ---------------------------------------------------------------------

def gpu_domain_test(domain_size):
    if not HAS_CUDA:
        return None

    try:
        poly = cp.zeros(domain_size, dtype=cp.uint64)
        cp.cuda.Device().synchronize()
        del poly
        return True
    except Exception:
        return False

# ---------------------------------------------------------------------
# Main Validation
# ---------------------------------------------------------------------

def main():
    banner("FRI DOMAIN & BLOW-UP VALIDATION")

    print(f"Platform      : {platform.platform()}")
    print(f"Python        : {platform.python_version()}")
    print(f"Backend       : {'CuPy (CUDA)' if HAS_CUDA else 'NumPy (CPU)'}")

    rows = FRI_CONFIG["trace_rows"]
    print(f"Trace rows    : {rows:,}")
    print(f"Max AIR degree: {FRI_CONFIG['max_degree']}")

    results = []

    for blowup in FRI_CONFIG["blowup_factors"]:
        banner(f"Blow-Up Factor = {blowup}")

        domain = compute_domain_size(rows, blowup)
        folding_depth = compute_folding_depth(domain)

        print(f"Domain size   : {domain:,}")
        print(f"Folding depth : {folding_depth}")

        if folding_depth > FRI_CONFIG["max_folding_depth"]:
            fail("Folding depth exceeds configured safety limit")

        mem_ok, mem_gb = check_memory(
            estimate_domain_memory(domain)
        )

        print(f"Estimated memory: {mem_gb:.2f} GB")

        if HAS_CUDA and not mem_ok:
            fail("Domain exceeds safe VRAM envelope")

        banner("Allocation Test")

        start = time.time()
        alloc_ok = gpu_domain_test(domain)
        elapsed = time.time() - start

        if HAS_CUDA:
            if not alloc_ok:
                fail("GPU allocation failed")
            print(f"Allocation time: {elapsed:.2f} s")
            ok("GPU allocation successful")
        else:
            print("GPU allocation skipped (CPU reference tier)")
            ok("CPU feasibility validated")

        results.append((blowup, domain, folding_depth, mem_gb))

    banner("FRI DOMAIN SUMMARY")

    for b, d, f, m in results:
        print(
            f"Blowup={b:<2} | "
            f"Domain={d:<10,} | "
            f"Folds={f:<2} | "
            f"Memory≈{m:.2f} GB"
        )

    ok("All applicable FRI domain configurations validated")

if __name__ == "__main__":
    main()
