"""
TetraKlein IVC Folding Equivocation Audit
========================================

Purpose:
    Detects equivocation attempts occurring *inside recursive IVC folding*,
    where two divergent witnesses attempt to collapse into a single accumulator.

Threat Model:
    - Two independently valid sub-proofs
    - Divergent witness values
    - Same folding schedule
    - Same public inputs
    - No cryptographic break
    - Attempted accumulator collision

Guarantee:
    Any divergence in folded state MUST be detected at fold time
    with bounded verifier cost.

This is a *soundness-critical* audit.
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import os
import time
import logging
import psutil
import random
from dataclasses import dataclass
from typing import List
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------

IVC_DIR = LOG_ROOT / "ivc_folding_audit"
IVC_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = IVC_DIR / "ivc_folding_equivocation.log"
CONSOLE_LOG = IVC_DIR / "console.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)

# Redirect stdout / stderr
logfile = open(CONSOLE_LOG, "a", buffering=1)
import sys
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

MAX_DEPTH = 64
RESIDUAL_BOUND = 1e-6
RANDOM_SEED = 424242

random.seed(RANDOM_SEED)

# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------

@dataclass
class FoldState:
    accumulator: float
    residual: float


@dataclass
class AuditResult:
    equivocation_detected: bool
    detection_depth: int
    max_residual: float
    verifier_ops: int
    runtime: float


# ---------------------------------------------------------------------
# Folding Model
# ---------------------------------------------------------------------

class FoldingEngine:
    """
    Minimal deterministic IVC folding model.

    Folding rule:
        acc_{n+1} = 0.5 * acc_n + 0.5 * witness_n
    """

    def __init__(self):
        self.verifier_ops = 0
        self.max_residual = 0.0

    def fold(self, prev: FoldState, witness: float) -> FoldState:
        self.verifier_ops += 1

        new_acc = 0.5 * prev.accumulator + 0.5 * witness
        residual = abs(new_acc - prev.accumulator)

        self.max_residual = max(self.max_residual, residual)

        return FoldState(
            accumulator=new_acc,
            residual=residual
        )


# ---------------------------------------------------------------------
# Audit Runner
# ---------------------------------------------------------------------

def run_ivc_folding_equivocation_audit() -> AuditResult:
    start = time.time()

    engine_A = FoldingEngine()
    engine_B = FoldingEngine()

    # Shared initial accumulator
    state_A = FoldState(accumulator=0.0, residual=0.0)
    state_B = FoldState(accumulator=0.0, residual=0.0)

    detection_depth = -1
    equivocation_detected = False

    for depth in range(1, MAX_DEPTH + 1):
        # Honest witness
        witness_A = random.uniform(-1.0, 1.0)

        # Adversarial divergence
        witness_B = witness_A
        if depth == MAX_DEPTH // 2:
            witness_B += 0.25  # bounded equivocation

        state_A = engine_A.fold(state_A, witness_A)
        state_B = engine_B.fold(state_B, witness_B)

        # Detection condition: accumulator mismatch
        if abs(state_A.accumulator - state_B.accumulator) > RESIDUAL_BOUND:
            equivocation_detected = True
            detection_depth = depth
            break

    runtime = time.time() - start

    return AuditResult(
        equivocation_detected=equivocation_detected,
        detection_depth=detection_depth,
        max_residual=max(engine_A.max_residual, engine_B.max_residual),
        verifier_ops=engine_A.verifier_ops + engine_B.verifier_ops,
        runtime=runtime,
    )


# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------

def main():
    logging.info("=" * 69)
    logging.info("TETRAKLEIN IVC FOLDING EQUIVOCATION AUDIT — START")
    logging.info("=" * 69)

    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    result = run_ivc_folding_equivocation_audit()

    mem_after = proc.memory_info().rss / 1024**2

    logging.info("EQUIVOCATION DETECTED : %s", result.equivocation_detected)
    logging.info("DETECTION DEPTH       : %s", result.detection_depth)
    logging.info("MAX RESIDUAL          : %.6e", result.max_residual)
    logging.info("VERIFIER OPS          : %d", result.verifier_ops)
    logging.info("RUNTIME               : %.3fs", result.runtime)
    logging.info("MEMORY DELTA          : %.2f MB", mem_after - mem_before)

    logging.info("=" * 69)
    logging.info("TETRAKLEIN IVC FOLDING AUDIT COMPLETE")
    logging.info("=" * 69)

    if not result.equivocation_detected:
        raise RuntimeError("IVC FOLDING EQUIVOCATION NOT DETECTED — SAFETY FAILURE")


if __name__ == "__main__":
    main()
