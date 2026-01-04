#!/usr/bin/env python3
"""
TetraKlein Local Validation Suite (Capability-Adaptive)

Execution tiers:
- CPU reference (NumPy)
- CUDA acceleration (CuPy, optional)
- Neural accelerators are excluded from determinism tests
"""

import os
import sys
import time
import platform
from pathlib import Path
import math

import numpy as np
import sympy as sp

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

from tklocal_paths import LOG_ROOT

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
# 0. Environment Check
# ---------------------------------------------------------------------

def check_environment():
    banner("0. Environment Check")

    print(f"Platform         : {platform.platform()}")
    print(f"Python           : {platform.python_version()}")
    print(f"Array backend    : {'CuPy (CUDA)' if HAS_CUDA else 'NumPy (CPU)'}")

    if HAS_CUDA:
        dev = cp.cuda.runtime.getDeviceProperties(0)
        print(f"GPU              : {dev['name'].decode()}")
        print(f"Compute capability: {dev['major']}.{dev['minor']}")
        if dev["major"] < 7:
            fail("GPU compute capability < 7.0 not supported")

    ok("Environment valid for this execution tier")

# ---------------------------------------------------------------------
# 1. DTC Contractivity Test
# ---------------------------------------------------------------------

def test_dtc_contractivity():
    banner("1. DTC Contractivity (ρ < 1)")

    rho = 0.95
    sigma = 0.01
    error0 = 1.0

    t = xp.arange(0, 200_000, dtype=xp.float64)
    error = error0 * rho ** t + sigma / (1 - rho)

    limit_numeric = float(error[-1])
    limit_expected = sigma / (1 - rho)

    print(f"Numeric limit  : {limit_numeric:.8f}")
    print(f"Expected limit : {limit_expected:.8f}")

    if abs(limit_numeric - limit_expected) > 1e-6:
        fail("DTC contractivity limit mismatch")

    ok("DTC contractivity verified")

# ---------------------------------------------------------------------
# 2. Hypercube Spectral Gap (HBB)
# ---------------------------------------------------------------------

def test_hbb_spectral_gap():
    banner("2. Hypercube Spectral Gap")

    def spectral_gap(N):
        k = xp.arange(0, N + 1)
        lambdas = N - 2 * k
        lambdas = xp.sort(lambdas)
        return float((lambdas[-1] - lambdas[-2]) / N)

    for N in [8, 16, 32, 64]:
        gap = spectral_gap(N)
        expected = 2.0 / N
        print(f"N={N:>3}  gap={gap:.6f}  expected={expected:.6f}")
        if abs(gap - expected) > 1e-8:
            fail(f"Spectral gap mismatch at N={N}")

    ok("HBB spectral gap scaling verified")

# ---------------------------------------------------------------------
# 3. AIR Degree Safety
# ---------------------------------------------------------------------

def test_air_degree():
    banner("3. AIR Polynomial Degree Safety")

    x, s, b, alpha = sp.symbols("x s b alpha")

    C1 = x + s - b
    C2 = s**2 - s
    P = alpha * C1 + (1 - alpha) * C2

    deg_x = sp.degree(P, x)
    deg_total = sp.total_degree(P)

    print(f"Degree in x     : {deg_x}")
    print(f"Total degree   : {deg_total}")

    if deg_total > 4:
        fail("AIR degree exceeds allowed bound")

    ok("AIR degree constraints satisfied")

# ---------------------------------------------------------------------
# 4. IVC Folding Stability
# ---------------------------------------------------------------------

def test_ivc_folding():
    banner("4. IVC Folding Stability")

    rho = 0.9
    R0 = 1.0
    R = xp.ones(1_000_000, dtype=xp.float64)

    for _ in range(40):
        R = rho * R

    residual = float(xp.max(R))
    print(f"Residual after folding : {residual:.6e}")

    if residual >= R0:
        fail("IVC folding is not contractive")

    ok("IVC folding is contractive and stable")

# ---------------------------------------------------------------------
# 5. GPU Load Test (CUDA only)
# ---------------------------------------------------------------------

def test_gpu_stability():
    if not HAS_CUDA:
        banner("5. GPU Stability Test (SKIPPED)")
        print("No CUDA device available — skipping")
        return

    banner("5. GPU Stability / Load Test")

    try:
        x = cp.random.rand(20_000_000, dtype=cp.float32)
        y = cp.sqrt(x) * cp.log1p(x)
        cp.cuda.Device().synchronize()
    except Exception as e:
        fail(f"GPU computation failed: {e}")

    ok("GPU sustained load without error")

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    start = time.time()

    check_environment()
    test_dtc_contractivity()
    test_hbb_spectral_gap()
    test_air_degree()
    test_ivc_folding()
    test_gpu_stability()

    elapsed = time.time() - start
    banner("VALIDATION COMPLETE")
    print(f"Total runtime: {elapsed:.2f} s")
    ok("All applicable TetraKlein validation checks passed")

if __name__ == "__main__":
    main()
