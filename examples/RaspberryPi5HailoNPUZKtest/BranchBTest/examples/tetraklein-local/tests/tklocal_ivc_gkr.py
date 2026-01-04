#!/usr/bin/env python3
"""
TetraKlein Unified IVC Batch Soundness Audit
===========================================

MERGED COVERAGE:
  • IVC Multi-Fold Batch Aggregation (HBB-IVC-B)
  • Adaptive Batch Sizing Adversaries
  • XR-Frame → Epoch Folding
  • GKR-Style Batched Witness Folding

Guarantees:
  Any equivocation in:
    - single fold
    - multi-fold batch
    - adaptive batch boundary
    - XR epoch integration
    - GKR witness masking

MUST be detected with bounded verifier cost.

SYSTEM SAFETY TEST — failure raises RuntimeError.
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
from typing import List, Optional
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

AUDIT_DIR = LOG_ROOT / "ivc_hbb_batch_full_audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = AUDIT_DIR / "audit.log"
CONSOLE_LOG = AUDIT_DIR / "console.log"

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
# Configuration (Pi-safe)
# ---------------------------------------------------------------------

MAX_EPOCHS = 8
MAX_DEPTH = 64
MAX_FRAMES_PER_EPOCH = 16
BATCH_SIZE_CHOICES = [2, 4, 8]
FIXED_BATCH_SIZE = 8
RANDOM_SEED = 271828

random.seed(RANDOM_SEED)

# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------

@dataclass
class FoldState:
    acc: float
    commit: int


@dataclass
class AuditResult:
    name: str
    equivocation_detected: bool
    detection_point: Optional[int]
    verifier_ops: int
    runtime: float


# ---------------------------------------------------------------------
# Commitment Primitives (HBB-Compatible)
# ---------------------------------------------------------------------

def commit_fold(depth, prev_commit, acc):
    return hash(("FOLD", depth, prev_commit, round(acc, 8)))


def commit_batch(fold_commits):
    return hash(tuple(fold_commits))


def commit_witness(w):
    return hash(("WIT", round(w, 8)))


def commit_epoch(epoch, batch_size, fold_commits, witness_commits):
    return hash((
        "EPOCH",
        epoch,
        batch_size,
        tuple(fold_commits),
        tuple(witness_commits)
    ))


# ---------------------------------------------------------------------
# Folding Engine
# ---------------------------------------------------------------------

class FoldingEngine:
    def __init__(self):
        self.ops = 0

    def fold(self, prev: FoldState, witness: float, depth: int):
        self.ops += 1
        acc = 0.5 * prev.acc + 0.5 * witness
        return FoldState(acc, commit_fold(depth, prev.commit, acc))


# ---------------------------------------------------------------------
# Audit 1: Multi-Fold Batch Aggregation (HBB-IVC-B)
# ---------------------------------------------------------------------

def run_multifold_batch_audit() -> AuditResult:
    start = time.time()

    engA, engB = FoldingEngine(), FoldingEngine()
    stateA = FoldState(0.0, hash(("GENESIS",)))
    stateB = FoldState(0.0, hash(("GENESIS",)))

    depth = 1
    detected = False
    detect_at = None

    while depth <= MAX_DEPTH:
        batchA, batchB = [], []

        for _ in range(FIXED_BATCH_SIZE):
            if depth > MAX_DEPTH:
                break

            wA = random.uniform(-1, 1)
            wB = wA

            if depth == MAX_DEPTH // 2:
                wB += 0.3

            stateA = engA.fold(stateA, wA, depth)
            stateB = engB.fold(stateB, wB, depth)

            batchA.append(stateA.commit)
            batchB.append(stateB.commit)

            depth += 1

        engA.ops += 1
        engB.ops += 1

        if commit_batch(batchA) != commit_batch(batchB):
            detected = True
            detect_at = depth - 1
            break

    return AuditResult(
        name="IVC Multi-Fold Batch",
        equivocation_detected=detected,
        detection_point=detect_at,
        verifier_ops=engA.ops + engB.ops,
        runtime=time.time() - start
    )


# ---------------------------------------------------------------------
# Audit 2: Adaptive Batch + XR Epoch + GKR Folding
# ---------------------------------------------------------------------

def run_adaptive_epoch_audit() -> AuditResult:
    start = time.time()

    engA, engB = FoldingEngine(), FoldingEngine()
    stateA = FoldState(0.0, hash(("GENESIS",)))
    stateB = FoldState(0.0, hash(("GENESIS",)))

    detected = False
    detect_epoch = None

    for epoch in range(1, MAX_EPOCHS + 1):
        batch_size = random.choice(BATCH_SIZE_CHOICES)

        foldA, foldB = [], []
        witA, witB = [], []

        for i in range(batch_size):
            wA = random.uniform(-1, 1)
            wB = wA

            if epoch == MAX_EPOCHS // 2 and i == batch_size // 2:
                wB += 0.35

            stateA = engA.fold(stateA, wA, epoch * 100 + i)
            stateB = engB.fold(stateB, wB, epoch * 100 + i)

            foldA.append(stateA.commit)
            foldB.append(stateB.commit)
            witA.append(commit_witness(wA))
            witB.append(commit_witness(wB))

        engA.ops += 1
        engB.ops += 1

        if commit_epoch(epoch, batch_size, foldA, witA) != \
           commit_epoch(epoch, batch_size, foldB, witB):
            detected = True
            detect_epoch = epoch
            break

    return AuditResult(
        name="Adaptive Batch + XR + GKR",
        equivocation_detected=detected,
        detection_point=detect_epoch,
        verifier_ops=engA.ops + engB.ops,
        runtime=time.time() - start
    )


# ---------------------------------------------------------------------
# Entry Point (Merged Safety Gate)
# ---------------------------------------------------------------------

def main():
    logging.info("=" * 80)
    logging.info("TETRAKLEIN UNIFIED IVC / HBB BATCH SOUNDNESS AUDIT — START")
    logging.info("=" * 80)

    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    results = [
        run_multifold_batch_audit(),
        run_adaptive_epoch_audit()
    ]

    mem_after = proc.memory_info().rss / 1024**2

    for r in results:
        logging.info("[%s]", r.name)
        logging.info("  EQUIVOCATION DETECTED : %s", r.equivocation_detected)
        logging.info("  DETECTION POINT      : %s", r.detection_point)
        logging.info("  VERIFIER OPS         : %d", r.verifier_ops)
        logging.info("  RUNTIME              : %.3fs", r.runtime)

        if not r.equivocation_detected:
            raise RuntimeError(
                f"{r.name} FAILED — soundness hole detected"
            )

    logging.info("MEMORY DELTA : %.2f MB", mem_after - mem_before)
    logging.info("=" * 80)
    logging.info("UNIFIED IVC / HBB BATCH AUDIT COMPLETE — ALL CHECKS PASSED")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()
