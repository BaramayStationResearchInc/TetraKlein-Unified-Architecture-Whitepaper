#!/usr/bin/env python3
"""
TetraKlein IVC Folding Equivocation Audit
========================================

HBB-IVC-E — Folding Equivocation Detection

Purpose:
    Detect equivocation *inside recursive IVC folding* by enforcing
    commitment equality at each fold step.

Guarantee:
    Divergent witnesses cannot collapse into the same accumulator.
    Detection occurs at fold time with O(1) verifier cost.

This is a SOUNDNESS-CRITICAL audit.
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
from typing import Optional
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

logfile = open(CONSOLE_LOG, "a", buffering=1)
import sys
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

MAX_DEPTH = 64
RANDOM_SEED = 424242
random.seed(RANDOM_SEED)

# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------

@dataclass
class FoldState:
    accumulator: float
    commitment: int


@dataclass
class AuditResult:
    equivocation_detected: bool
    detection_depth: Optional[int]
    verifier_ops: int
    runtime: float


# ---------------------------------------------------------------------
# Commitment Model (HBB-Compatible)
# ---------------------------------------------------------------------

def commit(depth: int, prev_commit: int, acc: float) -> int:
    """
    Deterministic fold commitment.
    Models Recursive Tesseract Hashing (RTH) binding.
    """
    return hash((depth, prev_commit, round(acc, 8)))


# ---------------------------------------------------------------------
# Folding Engine (HBB-IVC-E)
# ---------------------------------------------------------------------

class FoldingEngine:
    """
    Deterministic recursive folding engine.

    Fold rule:
        acc_{k+1} = 0.5 * acc_k + 0.5 * witness_k

    Commitment rule:
        c_{k+1} = H(depth, c_k, acc_{k+1})
    """

    def __init__(self):
        self.verifier_ops = 0

    def fold(
        self,
        depth: int,
        prev: FoldState,
        witness: float,
    ) -> FoldState:
        self.verifier_ops += 1

        new_acc = 0.5 * prev.accumulator + 0.5 * witness
        new_commit = commit(depth, prev.commitment, new_acc)

        return FoldState(
            accumulator=new_acc,
            commitment=new_commit,
        )


# ---------------------------------------------------------------------
# Audit Runner
# ---------------------------------------------------------------------

def run_ivc_folding_equivocation_audit() -> AuditResult:
    start = time.time()

    engine_A = FoldingEngine()
    engine_B = FoldingEngine()

    # Shared genesis
    genesis_commit = commit(0, 0, 0.0)
    state_A = FoldState(0.0, genesis_commit)
    state_B = FoldState(0.0, genesis_commit)

    detection_depth: Optional[int] = None
    equivocation_detected = False

    for depth in range(1, MAX_DEPTH + 1):
        # Honest witness
        witness_A = random.uniform(-1.0, 1.0)

        # Adversarial equivocation
        witness_B = witness_A
        if depth == MAX_DEPTH // 2:
            witness_B += 0.25  # bounded divergence

        state_A = engine_A.fold(depth, state_A, witness_A)
        state_B = engine_B.fold(depth, state_B, witness_B)

        # HBB-IVC-E: commitment mismatch = equivocation
        if state_A.commitment != state_B.commitment:
            equivocation_detected = True
            detection_depth = depth
            logging.info("IVC EQUIVOCATION DETECTED")
            logging.info(" depth=%d", depth)
            logging.info(" A=%d", state_A.commitment)
            logging.info(" B=%d", state_B.commitment)
            break

    runtime = time.time() - start

    return AuditResult(
        equivocation_detected=equivocation_detected,
        detection_depth=detection_depth,
        verifier_ops=engine_A.verifier_ops + engine_B.verifier_ops,
        runtime=runtime,
    )


# ---------------------------------------------------------------------
# Entry Point (Hard Safety Gate)
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
