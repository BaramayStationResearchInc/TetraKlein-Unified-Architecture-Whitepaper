#!/usr/bin/env python3
"""
TetraKlein Local Epoch Aggregation Validation
Target Hardware:
  - RTX 2070 SUPER (8 GB VRAM)
Purpose:
  - Map XR frame rates to proof aggregation windows
  - Verify prover + verifier latency feasibility
  - Establish safe epoch sizes and margins
"""
import os
import math
import time
import sys
import datetime
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
# Measured Inputs (from previous scripts)
# ---------------------------------------------------------------------

MEASURED = {
    # From tklocal_prover_budget.py (example conservative values)
    "prover_time_per_proof_s": 0.35,     # seconds per proof (measured)
    "verifier_latency_ms": 0.03,         # per-proof verifier latency
}

# ---------------------------------------------------------------------
# XR / Epoch Configuration
# ---------------------------------------------------------------------

XR_CONFIG = {
    "frame_rates": [60, 90, 120],        # Hz
    "epoch_windows_ms": [50, 100, 250],  # aggregation windows
    "safety_margin": 0.70,               # use only 70% of capacity
}


# ---------------------------------------------------------------------
# Core Calculations
# ---------------------------------------------------------------------

def frames_per_epoch(fps, epoch_ms):
    return int(fps * (epoch_ms / 1000.0))


def proofs_per_epoch(frames):
    """
    One proof per XR frame (worst case).
    """
    return frames


def epoch_prover_time_s(proofs):
    return proofs * MEASURED["prover_time_per_proof_s"]


def epoch_verifier_time_s(proofs):
    return proofs * (MEASURED["verifier_latency_ms"] / 1000.0)


# ---------------------------------------------------------------------
# Main Validation
# ---------------------------------------------------------------------

def main():
    banner("XR EPOCH AGGREGATION VALIDATION")

    print(f"Prover time / proof : {MEASURED['prover_time_per_proof_s']:.3f} s")
    print(f"Verifier latency    : {MEASURED['verifier_latency_ms']:.3f} ms")
    print(f"Safety margin       : {XR_CONFIG['safety_margin']*100:.0f}%")

    banner("XR RATE × EPOCH WINDOW ANALYSIS")

    viable = []

    for fps in XR_CONFIG["frame_rates"]:
        for epoch_ms in XR_CONFIG["epoch_windows_ms"]:
            frames = frames_per_epoch(fps, epoch_ms)
            proofs = proofs_per_epoch(frames)

            prover_t = epoch_prover_time_s(proofs)
            verifier_t = epoch_verifier_time_s(proofs)

            budget_s = epoch_ms / 1000.0
            usable_budget = budget_s * XR_CONFIG["safety_margin"]

            ok_epoch = prover_t <= usable_budget

            status = "OK" if ok_epoch else "NO"

            print(
                f"FPS={fps:<3} | "
                f"Epoch={epoch_ms:<3} ms | "
                f"Frames={frames:<3} | "
                f"Proofs={proofs:<3} | "
                f"Prover={prover_t:.2f} s | "
                f"Budget={usable_budget:.2f} s | "
                f"{status}"
            )

            if ok_epoch:
                viable.append((fps, epoch_ms, proofs))

    banner("VIABLE OPERATING POINTS")

    if not viable:
        fail("No XR-rate epoch configuration is feasible")

    for fps, epoch_ms, proofs in viable:
        print(
            f"FPS={fps:<3} | "
            f"Epoch={epoch_ms:<3} ms | "
            f"Proofs/Epoch={proofs}"
        )

    banner("ENGINEERING CONCLUSION")
    print(
    "• XR-rate operation is achievable via epoch aggregation"
)

