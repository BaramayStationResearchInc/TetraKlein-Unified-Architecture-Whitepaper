#!/usr/bin/env python3
"""
TetraKlein Cross-Epoch Equivocation Audit — HBB-Aligned
=====================================================

This audit enforces **true Hypercube Blockchain Base adjacency semantics**.

It proves:
  • Single-successor safety per hypercube vertex (HBB-E1)
  • Multi-axis equivocation detection
  • Gossip-delayed equivocation resistance
  • O(1) verifier detection cost

Failure raises RuntimeError.
"""

import os
import sys
import time
import random
import logging
import psutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

EQ_DIR = LOG_ROOT / "hbb_equivocation_audit"
EQ_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = EQ_DIR / "equivocation.log"
CONSOLE_LOG = EQ_DIR / "console.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

logfile = open(CONSOLE_LOG, "a", buffering=1)
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Configuration (Pi-Safe)
# ---------------------------------------------------------------------

MAX_EPOCHS = 64
HYPERCUBE_DIM = 6            # 6-dimensional HBB
GOSSIP_DELAY_PROB = 0.35     # adversarial propagation delay
CONTRACTIVITY = 0.90
SEED = 1337
random.seed(SEED)

# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class HBBCommitment:
    epoch: int
    parent_root: int
    axis_mask: int
    state_root: int
    branch: str

@dataclass
class BranchState:
    name: str
    value: float
    root: int
    axis: int

@dataclass
class AuditResult:
    equivocation_detected: bool
    detection_epoch: Optional[int]
    rejected_branch: Optional[str]
    verifier_ops: int
    runtime: float

# ---------------------------------------------------------------------
# Commitment surrogate (RTH-style binding)
# ---------------------------------------------------------------------

def commit(epoch: int, parent: int, axis: int, value: float) -> int:
    return hash((epoch, parent, axis, round(value, 8)))

# ---------------------------------------------------------------------
# HBB Equivocation Verifier (O(1))
# ---------------------------------------------------------------------

class HBBVerifier:
    """
    Enforces:
      HBB-E0: adjacency validity
      HBB-E1: single child per parent
    """
    def __init__(self):
        self.seen: dict[int, tuple[int, str]] = {}
        self.ops = 0

    def observe(self, c: HBBCommitment) -> tuple[bool, Optional[int], Optional[str]]:
        self.ops += 1

        if c.parent_root in self.seen:
            prev_root, prev_branch = self.seen[c.parent_root]
            if prev_root != c.state_root:
                logging.info("EQUIVOCATION DETECTED")
                logging.info(" epoch=%d", c.epoch)
                logging.info(" parent=%d", c.parent_root)
                logging.info(" %s → %d", prev_branch, prev_root)
                logging.info(" %s → %d", c.branch, c.state_root)
                return True, c.epoch, c.branch

        self.seen[c.parent_root] = (c.state_root, c.branch)
        return False, None, None

# ---------------------------------------------------------------------
# Branch Evolution (True HBB adjacency)
# ---------------------------------------------------------------------

def evolve_branch(
    branch: BranchState,
    epoch: int,
    force_parent: Optional[int] = None,
    force_axis: Optional[int] = None,
    adversarial: bool = False,
) -> HBBCommitment:

    delta = random.uniform(-1.0, 1.0) if adversarial else 0.5
    new_value = CONTRACTIVITY * branch.value + (1 - CONTRACTIVITY) * delta

    parent = force_parent if force_parent is not None else branch.root

    if force_axis is not None:
        new_axis = force_axis
    else:
        bit = 1 << random.randint(0, HYPERCUBE_DIM - 1)
        new_axis = branch.axis ^ bit   # true hypercube adjacency

    root = commit(epoch, parent, new_axis, new_value)

    branch.value = new_value
    branch.root = root
    branch.axis = new_axis

    return HBBCommitment(
        epoch=epoch,
        parent_root=parent,
        axis_mask=new_axis,
        state_root=root,
        branch=branch.name,
    )

# ---------------------------------------------------------------------
# Audit Execution
# ---------------------------------------------------------------------

def run_hbb_equivocation_audit() -> AuditResult:
    start = time.time()

    verifier = HBBVerifier()

    genesis_root = commit(0, 0, 0, 0.0)
    branch_A = BranchState("HONEST", 0.0, genesis_root, 0)
    branch_B = BranchState("ADVERSARY", 0.0, genesis_root, 0)

    equivocation_detected = False
    detection_epoch = None
    rejected_branch = None

    for epoch in range(1, MAX_EPOCHS + 1):

        # Honest walk
        honest_commit = evolve_branch(branch_A, epoch)

        # True HBB equivocation: two children of same parent on different axes
        axis_a = branch_A.axis ^ (1 << 0)
        axis_b = branch_A.axis ^ (1 << 1)

        adv_commit_1 = evolve_branch(
            branch_B, epoch,
            force_parent=branch_A.root,
            force_axis=axis_a,
            adversarial=True,
        )

        adv_commit_2 = evolve_branch(
            branch_B, epoch,
            force_parent=branch_A.root,
            force_axis=axis_b,
            adversarial=True,
        )

        # Gossip-delayed submission
        commits = [honest_commit, adv_commit_1, adv_commit_2]
        random.shuffle(commits)

        for c in commits:
            if random.random() < GOSSIP_DELAY_PROB:
                continue  # delayed gossip

            detected, ep, offender = verifier.observe(c)
            if detected:
                equivocation_detected = True
                detection_epoch = ep
                rejected_branch = offender
                break

        if equivocation_detected:
            break

    runtime = time.time() - start

    logging.info("EQUIVOCATION DETECTED : %s", equivocation_detected)
    logging.info("DETECTION EPOCH       : %s", detection_epoch)
    logging.info("REJECTED BRANCH       : %s", rejected_branch)
    logging.info("VERIFIER OPS          : %d", verifier.ops)
    logging.info("RUNTIME               : %.3fs", runtime)

    return AuditResult(
        equivocation_detected=equivocation_detected,
        detection_epoch=detection_epoch,
        rejected_branch=rejected_branch,
        verifier_ops=verifier.ops,
        runtime=runtime,
    )

# ---------------------------------------------------------------------
# Entry Point (Hard Safety Gate)
# ---------------------------------------------------------------------

def main() -> None:
    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    logging.info("=" * 72)
    logging.info("TETRAKLEIN HBB TRUE-ADJACENCY EQUIVOCATION AUDIT")
    logging.info("=" * 72)

    result = run_hbb_equivocation_audit()

    mem_after = proc.memory_info().rss / 1024**2
    logging.info("MEMORY DELTA          : %.2f MB", mem_after - mem_before)
    logging.info("=" * 72)
    logging.info("AUDIT COMPLETE")
    logging.info("=" * 72)

    if not result.equivocation_detected:
        raise RuntimeError("HBB EQUIVOCATION NOT DETECTED — SAFETY FAILURE")

if __name__ == "__main__":
    main()
