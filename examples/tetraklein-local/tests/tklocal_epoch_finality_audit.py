"""
TetraKlein Epoch Finality Window Audit
=====================================

Purpose:
    Enforces immutability of finalized epochs under delayed,
    replayed, or adversarially scheduled inputs.

Invariant:
    Once an epoch exits the finality window, no conflicting
    ancestry may be accepted.

This is a SYSTEM SAFETY TEST.
Not a cryptographic proof.

Author: Baramay Station Research Inc.
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
# Logging Setup (TEST-SPECIFIC)
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

# Redirect stdout / stderr
logfile = open(CONSOLE_LOG, "a", buffering=1)
import sys
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Configuration
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
    parent: Optional[int]
    root: int
    finalized: bool = False


@dataclass
class AuditResult:
    safety_ok: bool
    final_root: int
    detection_epoch: Optional[int]
    rejected_parent: Optional[int]
    verifier_ops: int
    runtime: float


# ---------------------------------------------------------------------
# Ledger Model
# ---------------------------------------------------------------------

class EpochLedger:
    """
    Minimal ledger enforcing:
        - single parent per epoch
        - strict finality
        - rejection of late ancestry
    """

    def __init__(self):
        self.nodes: Dict[int, EpochNode] = {}
        self.final_root: Optional[int] = None
        self.verifier_ops = 0

    def add_epoch(self, epoch: int, parent: Optional[int]) -> int:
        self.verifier_ops += 1
        root = hash((epoch, parent))
        self.nodes[epoch] = EpochNode(epoch, parent, root)
        return root

    def finalize_up_to(self, epoch: int):
        for e, node in self.nodes.items():
            if e <= epoch:
                node.finalized = True
                self.final_root = node.root

    def try_late_injection(self, epoch: int, parent: int) -> bool:
        """
        Attempt to inject ancestry referencing finalized history.
        Must be rejected.
        """
        self.verifier_ops += 1

        if parent in self.nodes and self.nodes[parent].finalized:
            return False

        self.nodes[epoch] = EpochNode(epoch, parent, hash((epoch, parent)))
        return True


# ---------------------------------------------------------------------
# Audit Runner
# ---------------------------------------------------------------------

def run_epoch_finality_audit() -> AuditResult:
    start = time.time()
    ledger = EpochLedger()

    # Honest history build
    for e in range(MAX_EPOCHS):
        parent = e - 1 if e > 0 else None
        ledger.add_epoch(e, parent)

        if e >= FINALITY_WINDOW:
            ledger.finalize_up_to(e - FINALITY_WINDOW)

    final_root = ledger.final_root

    # Adversarial delayed injection
    delayed_epoch = MAX_EPOCHS + ADVERSARIAL_DELAY
    target_parent = random.randint(0, MAX_EPOCHS - FINALITY_WINDOW - 1)

    accepted = ledger.try_late_injection(
        delayed_epoch,
        target_parent
    )

    return AuditResult(
        safety_ok=not accepted,
        final_root=final_root,
        detection_epoch=delayed_epoch if not accepted else None,
        rejected_parent=target_parent if not accepted else None,
        verifier_ops=ledger.verifier_ops,
        runtime=time.time() - start,
    )


# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------

def main():
    logging.info("=" * 70)
    logging.info("TETRAKLEIN EPOCH FINALITY WINDOW AUDIT — START")
    logging.info("=" * 70)

    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    result = run_epoch_finality_audit()

    mem_after = proc.memory_info().rss / 1024**2

    logging.info("SAFETY OK        : %s", result.safety_ok)
    logging.info("FINAL ROOT       : %s", result.final_root)
    logging.info("DETECTION EPOCH  : %s", result.detection_epoch)
    logging.info("REJECTED PARENT  : %s", result.rejected_parent)
    logging.info("VERIFIER OPS    : %d", result.verifier_ops)
    logging.info("RUNTIME         : %.3fs", result.runtime)
    logging.info("MEMORY DELTA    : %.2f MB", mem_after - mem_before)

    logging.info("=" * 70)
    logging.info("TETRAKLEIN EPOCH FINALITY AUDIT COMPLETE")
    logging.info("=" * 70)

    if not result.safety_ok:
        raise RuntimeError("FINALITY VIOLATION DETECTED")


if __name__ == "__main__":
    main()
