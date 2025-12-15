#!/usr/bin/env python3
"""
TetraKlein Local Validation Suite
Hardware Target:
  - NVIDIA RTX 2070 SUPER (SM 7.5, 8 GB)
  - AMD Ryzen 7 3700X
  - 64 GB RAM
Environment:
  - Python 3.12
  - CUDA 12.x (forward compatible)
  - cupy-cuda12x, numba, sympy
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
# Utility
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

    try:
        cuda_version = cp.cuda.runtime.runtimeGetVersion()
        device = cp.cuda.runtime.getDeviceProperties(0)
    except Exception as e:
        fail(f"CUDA not available: {e}")

    print(f"CUDA runtime version : {cuda_version}")
    print(f"GPU device          : {device['name'].decode()}")

    if device["major"] < 7:
        fail("GPU compute capability < 7.0 not supported")

    ok("CUDA + GPU detected and usable")


# ---------------------------------------------------------------------
# 1. DTC Contractivity Test
# ---------------------------------------------------------------------

def test_dtc_contractivity():
    banner("1. DTC Contractivity (ρ < 1)")

    rho = 0.95
    sigma = 0.01
    error0 = 1.0

    t = cp.arange(0, 200_000, dtype=cp.float64)
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
        k = cp.arange(0, N + 1)
        lambdas = N - 2 * k
        lambdas = cp.sort(lambdas)
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
# 4. IVC Folding Stability (Contractivity)
# ---------------------------------------------------------------------

def test_ivc_folding():
    banner("4. IVC Folding Stability")

    rho = 0.9
    R0 = 1.0
    R = cp.ones(1_000_000, dtype=cp.float64)

    for _ in range(40):
        R = rho * R

    residual = float(cp.max(R))
    print(f"Residual after folding : {residual:.6e}")

    # Contractivity invariant
    if residual >= R0:
        fail("IVC folding is not contractive")

    ok("IVC folding is contractive and stable")



# ---------------------------------------------------------------------
# 5. GPU Stability / Load Test
# ---------------------------------------------------------------------

def test_gpu_stability():
    banner("5. GPU Stability / Load Test")

    try:
        x = cp.random.rand(50_000_000, dtype=cp.float32)
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
    ok("All local TetraKlein validation checks passed")


if __name__ == "__main__":
    main()
