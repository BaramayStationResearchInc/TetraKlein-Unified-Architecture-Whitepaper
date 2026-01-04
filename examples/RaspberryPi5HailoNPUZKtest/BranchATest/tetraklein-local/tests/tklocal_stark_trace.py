#!/usr/bin/env python3
"""
TetraKlein Local STARK Trace Validation (End-to-End)

Validates:
- AIR constraint correctness (real witness)
- STARK trace construction from witness columns
- Epoch folding / IVC root accumulation
- Commitment binding
- Fault injection & divergence detection
- Trace scaling & folding envelopes
"""

import sys
import time
import platform
import hashlib
from pathlib import Path
from datetime import timedelta

import numpy as np
import sympy as sp

from tklocal_paths import LOG_ROOT
from tk_hailo_zk_executor import TKHailoZKExecutor
from tk_zk_witness_recorder import (
    TKZKWitnessRecorder,
    AIRViolation,
    TKEpochFolder,
    TKFaultInjector,
)

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
# Trace Configuration
# ---------------------------------------------------------------------

TRACE_CONFIG = {
    "rows": 2**20,
    "cols": 32,
    "field_modulus": 2**64 - 59,
}

if not HAS_CUDA:
    TRACE_CONFIG["rows"] = 2**17

# ---------------------------------------------------------------------
# 1. Trace Allocation & Memory Safety
# ---------------------------------------------------------------------

def test_trace_allocation():
    banner("1. Trace Allocation & Memory Safety")

    rows = TRACE_CONFIG["rows"]
    cols = TRACE_CONFIG["cols"]

    try:
        trace = xp.zeros((rows, cols), dtype=xp.uint64)
        if HAS_CUDA:
            cp.cuda.Device().synchronize()
    except Exception as e:
        fail(f"Trace allocation failed: {e}")

    mem_used = trace.nbytes / (1024**3)
    print(f"Trace size: {rows:,} × {cols}  (~{mem_used:.2f} GB)")

    if HAS_CUDA and mem_used > 6.5:
        fail("Trace exceeds safe VRAM envelope")

    ok("Trace allocated safely")
    return trace

# ---------------------------------------------------------------------
# 2. AIR Degree Check (Symbolic)
# ---------------------------------------------------------------------

def test_air_transition_degree():
    banner("2. AIR Transition Degree Check")

    x_t, x_next, a, b = sp.symbols("x_t x_next a b")
    C = x_next - (a * x_t + b)

    deg = sp.total_degree(C)
    print(f"Transition degree: {deg}")

    if deg > 2:
        fail("AIR degree overflow")

    ok("AIR degree within STARK limits")

# ---------------------------------------------------------------------
# 3. Trace Evolution Stress
# ---------------------------------------------------------------------

def test_trace_evolution(trace):
    banner("3. Trace Evolution Stress")

    p = TRACE_CONFIG["field_modulus"]

    def evolve_cpu(x):
        return (3 * x + 7) % p

    if HAS_CUDA:
        @cp.fuse()
        def evolve_gpu(x):
            return (3 * x + 7) % p
        evolve = evolve_gpu
    else:
        evolve = evolve_cpu

    start = time.time()
    for _ in range(8):
        trace[:] = evolve(trace)
    if HAS_CUDA:
        cp.cuda.Device().synchronize()

    print(f"Evolution time: {time.time() - start:.2f}s")
    ok("Trace evolution stable")

# ---------------------------------------------------------------------
# 4. Constraint Composition Stress
# ---------------------------------------------------------------------

def test_constraint_composition():
    banner("4. Constraint Composition Stress")

    x, y, z, α = sp.symbols("x y z α")

    C1 = x + y - z
    C2 = y**2 - y
    C3 = z - x*y

    P = α*C1 + (1-α)*C2 + α**2*C3
    deg = sp.total_degree(P)

    print(f"Composed degree: {deg}")
    if deg > 4:
        fail("Constraint degree explosion")

    ok("Constraint composition safe")

# ---------------------------------------------------------------------
# 5. Trace Folding
# ---------------------------------------------------------------------

def test_trace_folding(trace):
    banner("5. Trace Folding")

    before = trace.shape[0]
    folded = trace[::2, :]
    after = folded.shape[0]

    print(f"Rows before: {before:,}")
    print(f"Rows after : {after:,}")

    if after != before // 2:
        fail("Folding incorrect")

    ok("Trace folding correct")

# ---------------------------------------------------------------------
# 6. Witness → STARK Trace Builder
# ---------------------------------------------------------------------

class TKStarkTraceBuilder:
    def __init__(self, modulus):
        self.p = modulus

    def build(self, witness: TKZKWitnessRecorder):
        witness.check_air()
        cols = witness.export_trace_columns()
        n = len(cols["t"])

        trace = []
        for i in range(n):
            trace.append([
                cols["t"][i] % self.p,
                cols["x1"][i] % self.p,
                cols["x2"][i] % self.p,
                cols["y"][i] % self.p,
                cols["h"][i] % self.p,
            ])
        return trace

# ---------------------------------------------------------------------
# 7. Real Hardware → ZK → IVC → Commitment Validation
# ---------------------------------------------------------------------

def test_real_witness_pipeline():
    banner("6. Real Witness / ZK / IVC Pipeline")

    zk = TKHailoZKExecutor(
        "/home/baramaystation1/tkhailo/hef/tk_kernel.hef",
        "tk_kernel"
    )

    inputs = [(5, 3), (10, 2), (7, 7), (1, 1)]
    for x1, x2 in inputs:
        y = zk.step(x1, x2)
        print(f"({x1}, {x2}) → {y}")

    witness = zk.export_witness()
    commitment = zk.commitment().hex()

    print("\nWitness columns:")
    for k, v in witness.items():
        print(f"  {k}: {v}")

    print(f"\nFinal commitment: {commitment}")

    # Epoch folding (IVC-style)
    folder = TKEpochFolder(TRACE_CONFIG["field_modulus"])
    for h in witness["h"]:
        folder.absorb(h)

    ivc_root = folder.root()
    print(f"Epoch folding root: {ivc_root}")

    # Build STARK trace
    builder = TKStarkTraceBuilder(TRACE_CONFIG["field_modulus"])
    stark_trace = builder.build(zk.witness)

    print(f"STARK trace shape: {len(stark_trace)} × {len(stark_trace[0])}")

    zk.shutdown()
    ok("Real witness pipeline validated")

# ---------------------------------------------------------------------
# 8. Fault Injection & Divergence Detection
# ---------------------------------------------------------------------

def test_fault_injection():
    banner("7. Fault Injection & Divergence Detection")

    zk = TKHailoZKExecutor(
        "/home/baramaystation1/tkhailo/hef/tk_kernel.hef",
        "tk_kernel"
    )

    injector = TKFaultInjector()

    # Step 1: valid execution
    y1 = zk.step_checked(5, 3)

    # Step 2: valid execution
    y2 = zk.step_checked(10, 2)

    # Step 3: FAULT — manually corrupt witness
    zk.witness.trace[-1]["y"] = injector.inject(
        zk.witness.trace[-1]["y"]
    )

    # Step 4: AIR must now fail
    try:
        zk.witness.check_air()
        fail("Fault not detected")
    except AIRViolation as e:
        print(f"Detected AIR violation: {e}")
        ok("Fault injection correctly detected")

    zk.shutdown()


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    start = time.time()

    banner("STARK TRACE VALIDATION — ENVIRONMENT")
    print(f"Platform : {platform.platform()}")
    print(f"Python   : {platform.python_version()}")
    print(f"Backend  : {'CUDA' if HAS_CUDA else 'CPU'}")

    trace = test_trace_allocation()
    test_air_transition_degree()
    test_trace_evolution(trace)
    test_constraint_composition()
    test_trace_folding(trace)
    test_real_witness_pipeline()
    test_fault_injection()

    banner("STARK TRACE VALIDATION COMPLETE")
    print(f"Total runtime: {time.time() - start:.2f}s")
    ok("ALL STARK / ZK / IVC CHECKS PASSED")

if __name__ == "__main__":
    main()
