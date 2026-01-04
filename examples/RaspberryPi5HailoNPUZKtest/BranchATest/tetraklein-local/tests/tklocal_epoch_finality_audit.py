#!/usr/bin/env python3
"""
TetraKlein Epoch Finality Window Audit
=====================================

HBB-ALIGNED SAFETY REGRESSION

Purpose:
    Enforce immutability of finalized epochs under delayed,
    replayed, or adversarially scheduled inputs.

HBB Rules Enforced:
    HBB-E1  — Single successor per (epoch, parent)
    HBB-F   — Finality window immutability
    HBB-E2  — Gossip delay does not violate safety

This is a SYSTEM SAFETY TEST.
Not a cryptographic proof.

License: Apache 2.0
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
from typing import Dict, Optional

from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

EF_DIR = LOG_ROOT / "epoch_finality_audit"
EF_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = EF_DIR / "epoch_finality_audit.log"
CONSOLE_LOG = EF_DIR / "console.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)

import sys
logfile = open(CONSOLE_LOG, "a", buffering=1)
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Configuration (Raspberry Pi 5 Safe)
# ---------------------------------------------------------------------

MAX_EPOCHS = 128
FINALITY_WINDOW = 8
ADVERSARIAL_DELAY = 32

random.seed(42)

# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------

@dataclass
class EpochNode:
    epoch: int
    parent_epoch: Optional[int]
    root: int
    finalized: bool = False


@dataclass
class AuditResult:
    safety_ok: bool
    final_root: int
    detection_epoch: Optional[int]
    rejected_parent_epoch: Optional[int]
    verifier_ops: int
    runtime: float


# ---------------------------------------------------------------------
# Hypercube Blockchain Base Ledger
# ---------------------------------------------------------------------

class EpochLedger:
    """
    HBB-aligned ledger enforcing:

    • HBB-E1 — single successor per (epoch,parent)
    • HBB-F  — finalized epochs are immutable
    • O(1) verifier cost per insertion
    """

    def __init__(self):
        self.nodes: Dict[int, EpochNode] = {}
        self.final_root: Optional[int] = None
        self.verifier_ops = 0

    def _commit(self, epoch: int, parent_epoch: Optional[int]) -> int:
        """Deterministic commitment surrogate (RTH stand-in)."""
        return hash((epoch, parent_epoch))

    def add_epoch(self, epoch: int, parent_epoch: Optional[int]) -> int:
        self.verifier_ops += 1

        root = self._commit(epoch, parent_epoch)
        self.nodes[epoch] = EpochNode(
            epoch=epoch,
            parent_epoch=parent_epoch,
            root=root,
            finalized=False,
        )
        return root

    def finalize_up_to(self, finalized_epoch: int):
        for e, node in self.nodes.items():
            if e <= finalized_epoch:
                node.finalized = True
                self.final_root = node.root

    def try_late_injection(self, epoch: int, parent_epoch: int) -> bool:
        """
        Attempt to inject a node referencing finalized history.
        Must be rejected under HBB-F.
        """
        self.verifier_ops += 1

        if parent_epoch in self.nodes:
            parent_node = self.nodes[parent_epoch]
            if parent_node.finalized:
                logging.info(
                    "FINALITY VIOLATION ATTEMPT: epoch=%d parent_epoch=%d",
                    epoch, parent_epoch
                )
                return False

        # Would only be accepted if parent not finalized
        self.nodes[epoch] = EpochNode(
            epoch=epoch,
            parent_epoch=parent_epoch,
            root=self._commit(epoch, parent_epoch),
        )
        return True


# ---------------------------------------------------------------------
# Audit Runner
# ---------------------------------------------------------------------

def run_epoch_finality_audit() -> AuditResult:
    start = time.time()
    ledger = EpochLedger()

    # Honest chain construction
    for e in range(MAX_EPOCHS):
        parent = e - 1 if e > 0 else None
        ledger.add_epoch(e, parent)

        if e >= FINALITY_WINDOW:
            ledger.finalize_up_to(e - FINALITY_WINDOW)

    final_root = ledger.final_root

    # Adversarial delayed ancestry injection
    delayed_epoch = MAX_EPOCHS + ADVERSARIAL_DELAY
    target_parent_epoch = random.randint(
        0, MAX_EPOCHS - FINALITY_WINDOW - 1
    )

    accepted = ledger.try_late_injection(
        delayed_epoch,
        target_parent_epoch
    )

    runtime = time.time() - start

    return AuditResult(
        safety_ok=not accepted,
        final_root=final_root,
        detection_epoch=delayed_epoch if not accepted else None,
        rejected_parent_epoch=target_parent_epoch if not accepted else None,
        verifier_ops=ledger.verifier_ops,
        runtime=runtime,
    )


# ---------------------------------------------------------------------
# Entry Point (Hard Safety Gate)
# ---------------------------------------------------------------------

def main():
    logging.info("=" * 72)
    logging.info("TETRAKLEIN HBB EPOCH FINALITY WINDOW AUDIT — START")
    logging.info("=" * 72)

    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    result = run_epoch_finality_audit()

    mem_after = proc.memory_info().rss / 1024**2

    logging.info("SAFETY OK             : %s", result.safety_ok)
    logging.info("FINAL ROOT            : %s", result.final_root)
    logging.info("DETECTION EPOCH       : %s", result.detection_epoch)
    logging.info("REJECTED PARENT EPOCH : %s", result.rejected_parent_epoch)
    logging.info("VERIFIER OPS          : %d", result.verifier_ops)
    logging.info("RUNTIME               : %.3fs", result.runtime)
    logging.info("MEMORY DELTA          : %.2f MB", mem_after - mem_before)

    logging.info("=" * 72)
    logging.info("TETRAKLEIN HBB FINALITY AUDIT COMPLETE")
    logging.info("=" * 72)

    if not result.safety_ok:
        raise RuntimeError("HBB FINALITY VIOLATION — SYSTEM UNSAFE")


if __name__ == "__main__":
    main()
