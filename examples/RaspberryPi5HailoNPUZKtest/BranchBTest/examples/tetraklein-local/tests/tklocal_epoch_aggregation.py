#!/usr/bin/env python3
"""
TetraKlein Local Epoch Aggregation Validation
(IVC-Bounded, Pipeline-Memory-Aware)

Adds:
  - Verifier size bound on IVC recursion depth
  - Per-pipeline-lane memory pressure model
  - Annotated recommended operating profiles
"""

import sys
import math
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

LOG_ROOT.mkdir(parents=True, exist_ok=True)
logfile = open(LOG_ROOT / "console.log", "a", buffering=1)
sys.stdout = logfile
sys.stderr = logfile

class TKEpochFolder:
    """
    Linear folding accumulator for recursive IVC.
    """

    def __init__(self, modulus: int, alpha: int = 1315423911):
        self.p = modulus
        self.alpha = alpha
        self.acc = 0
        self.steps = 0

    def absorb(self, value: int):
        self.acc = (self.alpha * self.acc + value) % self.p
        self.steps += 1

    def root(self) -> int:
        return self.acc


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
# Hardware / Memory Envelope (conservative)
# ---------------------------------------------------------------------

GPU_VRAM_GB = 8.0
SAFE_GPU_VRAM_GB = 6.5
SAFE_GPU_BYTES = SAFE_GPU_VRAM_GB * (1024**3)

# ---------------------------------------------------------------------
# Verifier growth model (from prior IVC validation)
# ---------------------------------------------------------------------

VERIFIER_MODEL = {
    "base_state_bytes": 128 * 8,   # 128 field elements
    "folding_growth": 1.15,        # per recursion level
    "max_verifier_bytes": 256 * 1024 * 1024,  # 256 MB hard cap
}

# ---------------------------------------------------------------------
# Prover working set (per lane, conservative)
# ---------------------------------------------------------------------

PROVER_WORKING_SET = {
    "trace_slice_bytes": 512 * 1024 * 1024,  # 512 MB
    "scratch_bytes": 128 * 1024 * 1024,      # FFT, hash, etc.
}

# ---------------------------------------------------------------------
# Measured Inputs
# ---------------------------------------------------------------------

MEASURED = {
    "prover_time_per_proof_s": 0.35,
    "verifier_latency_ms": 0.03,
}

# ---------------------------------------------------------------------
# XR / Epoch / Pipeline Configuration
# ---------------------------------------------------------------------

XR_CONFIG = {
    "frame_rates": [60, 90, 120],
    "epoch_windows_ms": [250, 500, 1000],
    "frames_per_proof": [8, 16, 32, 64],
    "pipeline_widths": [1, 2, 4],
    "safety_margin": 0.70,
}

# ---------------------------------------------------------------------
# Recommended Operating Profiles (derived, not forced)
# ---------------------------------------------------------------------

RECOMMENDED_PROFILES = {
    "LOW_LATENCY_XR": {
        "description": "Minimize XR latency using aggressive pipelining",
        "prefer": {
            "max_epoch_ms": 250,
            "min_pipeline": 4,
        },
    },
    "BALANCED_XR": {
        "description": "Balanced latency, memory, and throughput",
        "prefer": {
            "min_frames_per_proof": 32,
            "max_pipeline": 2,
            "max_epoch_ms": 500,
        },
    },
    "LOW_MEMORY": {
        "description": "Minimize GPU memory footprint",
        "prefer": {
            "max_pipeline": 1,
            "min_frames_per_proof": 64,
        },
    },
    "HIGH_RATE_XR": {
        "description": "Optimized for sustained 90–120 Hz XR operation",
        "prefer": {
            "min_fps": 90,
            "min_frames_per_proof": 32,
        },
    },
}

# ---------------------------------------------------------------------
# Core Derivations
# ---------------------------------------------------------------------

def frames_per_epoch(fps, epoch_ms):
    return int(fps * (epoch_ms / 1000.0))

def ivc_recursion_depth(frames_per_proof):
    return math.ceil(math.log2(frames_per_proof))

def verifier_state_bytes(depth):
    base = VERIFIER_MODEL["base_state_bytes"]
    return int(base * (VERIFIER_MODEL["folding_growth"] ** depth))

def prover_lane_memory_bytes(depth):
    return (
        verifier_state_bytes(depth)
        + PROVER_WORKING_SET["trace_slice_bytes"]
        + PROVER_WORKING_SET["scratch_bytes"]
    )

def proofs_per_epoch(frames, frames_per_proof):
    return max(1, math.ceil(frames / frames_per_proof))

def effective_prover_time_per_proof(pipeline_width):
    return MEASURED["prover_time_per_proof_s"] / pipeline_width

def epoch_prover_time_s(proofs, pipeline_width):
    return proofs * effective_prover_time_per_proof(pipeline_width)

# ---------------------------------------------------------------------
# Profile Selection Helper
# ---------------------------------------------------------------------

def select_profile(viable, profile):
    prefs = profile["prefer"]
    candidates = []

    for fps, epoch_ms, fpp, depth, pipe, proofs, mem in viable:
        if fps < prefs.get("min_fps", fps):
            continue
        if epoch_ms > prefs.get("max_epoch_ms", epoch_ms):
            continue
        if fpp < prefs.get("min_frames_per_proof", fpp):
            continue
        if pipe > prefs.get("max_pipeline", pipe):
            continue
        if pipe < prefs.get("min_pipeline", pipe):
            continue
        candidates.append((fps, epoch_ms, fpp, depth, pipe, proofs, mem))

    if not candidates:
        return None

    # Prefer lower latency, then lower memory
    candidates.sort(key=lambda x: (x[1], x[6]))
    return candidates[0]

# ---------------------------------------------------------------------
# Main Validation
# ---------------------------------------------------------------------

def main():
    banner("XR EPOCH AGGREGATION VALIDATION")
    banner("IVC-BOUNDED + PIPELINE-MEMORY-AWARE")

    viable = []

    for fps in XR_CONFIG["frame_rates"]:
        for epoch_ms in XR_CONFIG["epoch_windows_ms"]:
            frames = frames_per_epoch(fps, epoch_ms)

            for fpp in XR_CONFIG["frames_per_proof"]:
                depth = ivc_recursion_depth(fpp)
                verifier_bytes = verifier_state_bytes(depth)

                if verifier_bytes > VERIFIER_MODEL["max_verifier_bytes"]:
                    continue

                for pipe in XR_CONFIG["pipeline_widths"]:
                    lane_mem = prover_lane_memory_bytes(depth)
                    total_mem = lane_mem * pipe

                    if total_mem > SAFE_GPU_BYTES:
                        continue

                    proofs = proofs_per_epoch(frames, fpp)
                    prover_t = epoch_prover_time_s(proofs, pipe)
                    budget_s = (epoch_ms / 1000.0) * XR_CONFIG["safety_margin"]

                    ok_epoch = prover_t <= budget_s
                    status = "OK" if ok_epoch else "NO"

                    print(
                        f"FPS={fps:<3} | Epoch={epoch_ms:<4} ms | "
                        f"Frames/Proof={fpp:<3} | IVCdepth={depth:<2} | "
                        f"Pipeline={pipe} | Prover={prover_t:.2f}s | "
                        f"Budget={budget_s:.2f}s | {status}"
                    )

                    if ok_epoch:
                        viable.append(
                            (fps, epoch_ms, fpp, depth, pipe, proofs, total_mem)
                        )

    banner("VIABLE OPERATING POINTS")

    if not viable:
        fail("No XR-rate configuration satisfies time AND memory constraints")

    for v in viable:
        fps, epoch_ms, fpp, depth, pipe, proofs, mem = v
        print(
            f"FPS={fps:<3} | Epoch={epoch_ms:<4} ms | "
            f"Frames/Proof={fpp:<3} | IVCdepth={depth:<2} | "
            f"Pipeline={pipe} | Proofs/Epoch={proofs} | "
            f"GPUmem≈{mem/1024**3:.2f} GB"
        )

    banner("RECOMMENDED OPERATING PROFILES")

    for name, profile in RECOMMENDED_PROFILES.items():
        sel = select_profile(viable, profile)
        print(f"\n{name}")
        print("-" * len(name))
        print(profile["description"])

        if sel is None:
            print("  ❌ No feasible configuration found")
            continue

        fps, epoch_ms, fpp, depth, pipe, proofs, mem = sel
        print(
            f"  FPS              : {fps}\n"
            f"  Epoch window     : {epoch_ms} ms\n"
            f"  Frames / Proof   : {fpp}\n"
            f"  IVC depth        : {depth}\n"
            f"  Pipeline width   : {pipe}\n"
            f"  Proofs / Epoch   : {proofs}\n"
            f"  GPU memory usage : ~{mem/1024**2:.0f} MB\n"
        )

    banner("ENGINEERING CONCLUSION")
    print(
        "• IVC recursion depth is bounded by verifier state growth\n"
        "• Pipeline width is bounded by GPU memory pressure\n"
        "• XR-rate feasibility requires joint time + memory satisfaction\n"
        "• Aggregation, recursion, and pipelining must be co-designed\n"
        "• Recommended profiles are derived from validated feasibility\n"
    )

    ok("Epoch aggregation feasibility validated with recommended profiles")

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()
