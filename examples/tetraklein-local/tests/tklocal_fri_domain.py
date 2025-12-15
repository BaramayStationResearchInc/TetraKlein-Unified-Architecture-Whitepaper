#!/usr/bin/env python3
"""
TetraKlein Local FRI Domain Validation
Target Hardware:
  - RTX 2070 SUPER (8 GB VRAM)
  - Ryzen 7 3700X
Purpose:
  - Validate FRI domain sizing
  - Check blow-up factor feasibility
  - Confirm folding depth bounds
"""
import os
import datetime
import sys
import math
import time


import cupy as cp
import numpy as np
from tklocal_paths import LOG_ROOT

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
# 0. Hardware Envelope
# ---------------------------------------------------------------------

VRAM_GB = 8.0
SAFE_VRAM_GB = 6.5      # conservative usable envelope
BYTES_PER_FIELD = 8    # uint64 field elements


# ---------------------------------------------------------------------
# 1. FRI Parameter Space
# ---------------------------------------------------------------------

FRI_CONFIG = {
    "trace_rows": 2**20,          # from tklocal_stark_trace
    "max_degree": 4,              # post-composition bound
    "blowup_factors": [2, 4, 8],
    "max_folding_depth": int(os.environ.get("MAX_FRI_FOLDING_DEPTH", 24)),
      # sanity limit
}


# ---------------------------------------------------------------------
# 2. Domain Size Computation
# ---------------------------------------------------------------------

def compute_domain_size(rows, blowup):
    """
    FRI domain size = next power of two >= rows * blowup
    """
    size = rows * blowup
    return 1 << (size - 1).bit_length()


# ---------------------------------------------------------------------
# 3. Memory Feasibility Check
# ---------------------------------------------------------------------

def estimate_domain_memory(domain_size, columns=1):
    """
    Memory for one polynomial over the domain
    """
    return domain_size * columns * BYTES_PER_FIELD


def check_memory(bytes_required):
    gb = bytes_required / (1024**3)
    return gb <= SAFE_VRAM_GB, gb


# ---------------------------------------------------------------------
# 4. Folding Depth Bound
# ---------------------------------------------------------------------

def compute_folding_depth(domain_size):
    """
    Folding depth = log2(domain_size)
    """
    return int(math.log2(domain_size))


# ---------------------------------------------------------------------
# 5. GPU Allocation Test
# ---------------------------------------------------------------------

def gpu_domain_test(domain_size):
    """
    Attempt allocation to confirm runtime feasibility
    """
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

    rows = FRI_CONFIG["trace_rows"]
    print(f"Trace rows: {rows:,}")
    print(f"Max AIR degree: {FRI_CONFIG['max_degree']}")

    results = []

    for blowup in FRI_CONFIG["blowup_factors"]:
        banner(f"Blow-Up Factor = {blowup}")

        domain = compute_domain_size(rows, blowup)
        folding_depth = compute_folding_depth(domain)

        print(f"Domain size        : {domain:,}")
        print(f"Folding depth      : {folding_depth}")

        if folding_depth > FRI_CONFIG["max_folding_depth"]:
            fail("Folding depth exceeds configured safety limit")

        mem_ok, mem_gb = check_memory(
            estimate_domain_memory(domain)
        )

        print(f"Domain memory usage: {mem_gb:.2f} GB")

        if not mem_ok:
            fail("Domain exceeds safe VRAM envelope")

        banner("GPU Allocation Test")
        start = time.time()
        alloc_ok = gpu_domain_test(domain)
        elapsed = time.time() - start

        if not alloc_ok:
            fail("GPU allocation failed")

        print(f"Allocation time: {elapsed:.2f} s")
        ok("Domain allocation successful")

        results.append((blowup, domain, folding_depth, mem_gb))

    banner("FRI DOMAIN SUMMARY")

    for b, d, f, m in results:
        print(
            f"Blowup={b:<2} | "
            f"Domain={d:<10,} | "
            f"Folds={f:<2} | "
            f"VRAM={m:.2f} GB"
        )

    ok("All FRI domain configurations validated")


if __name__ == "__main__":
    main()
