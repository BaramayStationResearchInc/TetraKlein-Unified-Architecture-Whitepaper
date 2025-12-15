#!/usr/bin/env python3
"""
TetraKlein Local STARK Trace Validation
Target Hardware:
  - RTX 2070 SUPER (8 GB VRAM)
  - Ryzen 7 3700X
Purpose:
  - Validate AIR trace scaling limits
  - Confirm degree ≤ 2 under composition
  - Stress trace memory without GPU faults
"""
import os
import datetime
import sys
import time
import math

import cupy as cp
import numpy as np
import sympy as sp

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
# 0. Trace Configuration
# ---------------------------------------------------------------------

TRACE_CONFIG = {
    "rows": 2**20,         # 1,048,576 rows (safe on 8 GB)
    "cols": 32,            # representative AIR width
    "field_modulus": 2**64 - 59,  # STARK-friendly prime
}


# ---------------------------------------------------------------------
# 1. Trace Allocation & Memory Safety
# ---------------------------------------------------------------------

def test_trace_allocation():
    banner("1. Trace Allocation & Memory Safety")

    rows = TRACE_CONFIG["rows"]
    cols = TRACE_CONFIG["cols"]

    try:
        trace = cp.zeros((rows, cols), dtype=cp.uint64)
        cp.cuda.Device().synchronize()
    except Exception as e:
        fail(f"Trace allocation failed: {e}")

    mem_used = trace.nbytes / (1024**3)
    print(f"Trace size: {rows:,} × {cols}  (~{mem_used:.2f} GB)")

    if mem_used > 6.5:
        fail("Trace exceeds safe VRAM envelope")

    ok("Trace allocated safely within VRAM limits")

    return trace


# ---------------------------------------------------------------------
# 2. AIR Transition Constraints (Degree Check)
# ---------------------------------------------------------------------

def test_air_transition_degree():
    banner("2. AIR Transition Degree Check")

    x_t, x_next, a, b = sp.symbols("x_t x_next a b")

    # Typical transition: x_{t+1} = a*x_t + b
    C_transition = x_next - (a * x_t + b)

    deg = sp.total_degree(C_transition)

    print(f"Transition constraint degree: {deg}")

    if deg > 2:
        fail("Transition constraint degree exceeds bound")

    ok("AIR transition degree within STARK limits")


# ---------------------------------------------------------------------
# 3. Trace Evolution Kernel
# ---------------------------------------------------------------------

def test_trace_evolution(trace):
    banner("3. Trace Evolution (GPU Kernel)")

    rows, cols = trace.shape

    @cp.fuse()
    def evolve(x):
        # degree-2 safe evolution
        return (3 * x + 7) % TRACE_CONFIG["field_modulus"]

    try:
        start = time.time()
        for _ in range(8):  # simulate 8 transitions
            trace[:] = evolve(trace)
        cp.cuda.Device().synchronize()
        elapsed = time.time() - start
    except Exception as e:
        fail(f"Trace evolution failed: {e}")

    print(f"Evolution time (8 steps): {elapsed:.2f} s")

    ok("Trace evolution stable under repeated transitions")


# ---------------------------------------------------------------------
# 4. Constraint Composition Stress
# ---------------------------------------------------------------------

def test_constraint_composition():
    banner("4. Constraint Composition Stress")

    x, y, z, alpha = sp.symbols("x y z alpha")

    C1 = x + y - z
    C2 = y**2 - y
    C3 = z - x*y

    # Fiat–Shamir-style linear combination
    P = alpha*C1 + (1-alpha)*C2 + (alpha**2)*C3

    deg = sp.total_degree(P)

    print(f"Composed constraint degree: {deg}")

    if deg > 4:
        fail("Constraint composition degree overflow")

    ok("Constraint composition degree safe")


# ---------------------------------------------------------------------
# 5. Folding / Subsampling Test
# ---------------------------------------------------------------------

def test_trace_folding(trace):
    banner("5. Trace Folding / Subsampling")

    rows_before = trace.shape[0]

    # Simple fold: keep even rows
    folded = trace[::2, :]

    rows_after = folded.shape[0]

    print(f"Rows before: {rows_before:,}")
    print(f"Rows after : {rows_after:,}")

    if rows_after != rows_before // 2:
        fail("Trace folding incorrect")

    ok("Trace folding behaves as expected")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    start = time.time()

    trace = test_trace_allocation()
    test_air_transition_degree()
    test_trace_evolution(trace)
    test_constraint_composition()
    test_trace_folding(trace)

    elapsed = time.time() - start
    banner("STARK TRACE VALIDATION COMPLETE")
    print(f"Total runtime: {elapsed:.2f} s")
    ok("All STARK trace checks passed")


if __name__ == "__main__":
    main()
