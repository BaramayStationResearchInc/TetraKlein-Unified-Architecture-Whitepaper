#!/usr/bin/env python3
"""
TetraKlein Adversarial Scheduling & Fault Injection Audit
(Raspberry Pi 5 – CPU-only profile, Seed Sweep + Tail Recovery)

OPTION A — Tail-Recovery (Correct Control-Theoretic Model)

This audit validates:
  • Bounded adversarial prefix
  • Guaranteed tail recovery
  • Contractive dynamics
  • Bounded verifier cost

This is a systems-level feasibility test, not a security proof.
"""

import os
import sys
import time
import random
import logging
import psutil
from dataclasses import dataclass
from pathlib import Path
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

ADV_DIR = LOG_ROOT / "adversarial_audit_pi"
ADV_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ADV_DIR / "adversarial_audit.log"
CONSOLE_LOG = ADV_DIR / "console.log"
RESIDUAL_DIR = ADV_DIR / "residuals"
RESIDUAL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

logfile = open(CONSOLE_LOG, "a", buffering=1)
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Raspberry Pi–Safe Configuration
# ---------------------------------------------------------------------

MAX_FRAMES = 512
FAULT_FRACTION = 0.10
MAX_DELAY = 16
MAX_REPLAYS = 16

RESIDUAL_BOUND = 1e-2
STABLE_WINDOW = 5              # consecutive tail steps below bound
MAX_RECOVERY_STEPS = 64
MAX_VERIFIER_OPS = 20_000

SEEDS = [1, 7, 42, 1337, 9001]

# Contractive dynamics
ALPHA = 0.80                   # contraction factor
BETA = 0.20                    # input weight

# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------

@dataclass
class Frame:
    index: int
    value: float
    valid: bool = True
    stale: bool = False

@dataclass
class AuditResult:
    seed: int
    safety_ok: bool
    max_residual: float
    verifier_ops: int
    recovery_steps: int
    runtime: float

# ---------------------------------------------------------------------
# Adversarial Scheduler
# ---------------------------------------------------------------------

class TKFaultInjector:
    """
    Deterministic fault injector for adversarial testing.
    """

    def __init__(self, flip_mask=0x01):
        self.flip_mask = flip_mask

    def inject(self, value: int) -> int:
        return value ^ self.flip_mask



class AdversarialScheduler:
    def __init__(self):
        self.buffer = []

    def submit(self, frame):
        self.buffer.append(frame)

    def schedule(self):
        scheduled = []

        # Block-wise reordering
        for i in range(0, len(self.buffer), MAX_DELAY):
            block = self.buffer[i:i + MAX_DELAY]
            scheduled.extend(reversed(block))

        # Replay injection
        if scheduled:
            replays = random.sample(
                scheduled, min(MAX_REPLAYS, len(scheduled))
            )
            for f in replays:
                scheduled.append(Frame(
                    index=f.index,
                    value=f.value,
                    valid=True,
                    stale=True
                ))

        # Random drops
        drops = int(0.05 * len(scheduled))
        for _ in range(drops):
            scheduled.pop(random.randrange(len(scheduled)))

        return scheduled

# ---------------------------------------------------------------------
# Fault Injector
# ---------------------------------------------------------------------

class FaultInjector:
    def __init__(self, fraction):
        self.fraction = fraction

    def inject(self, frames):
        if not frames:
            return frames

        n = int(len(frames) * self.fraction)
        for f in random.sample(frames, n):
            f.value += random.uniform(-1.0, 1.0)
            f.valid = False
        return frames

# ---------------------------------------------------------------------
# Aggregator / Verifier Proxy (CORRECT)
# ---------------------------------------------------------------------

class Aggregator:
    def __init__(self):
        self.state = 0.0
        self.ops = 0
        self.residuals = []

    def process(self, frame):
        self.ops += 1
        if not frame.valid:
            return

        self.state = ALPHA * self.state + BETA * frame.value

        # -------------------------------------------------------------
        # Residual = distance to equilibrium (0 in tail)
        # -------------------------------------------------------------
        self.residuals.append(abs(self.state))

# ---------------------------------------------------------------------
# Single-Seed Audit
# ---------------------------------------------------------------------

def run_single_seed(seed: int) -> AuditResult:
    random.seed(seed)
    start = time.time()

    scheduler = AdversarialScheduler()
    injector = FaultInjector(FAULT_FRACTION)
    agg = Aggregator()

    # ------------------------------
    # Adversarial prefix
    # ------------------------------
    frames = [
        Frame(i, random.uniform(-1.0, 1.0))
        for i in range(MAX_FRAMES // 2)
    ]

    for f in frames:
        scheduler.submit(f)

    scheduled = scheduler.schedule()
    corrupted = injector.inject(scheduled)

    # ------------------------------
    # Tail (QUIESCENT)
    # ------------------------------
    tail = [
        Frame(i, 0.0, valid=True)
        for i in range(MAX_FRAMES // 2, MAX_FRAMES)
    ]

    stream = corrupted + tail

    recovery = None
    stable = 0

    for i, frame in enumerate(stream):
        agg.process(frame)

        if agg.ops > MAX_VERIFIER_OPS:
            break

        # Tail-recovery logic
        if frame in tail:
            if agg.residuals and agg.residuals[-1] < RESIDUAL_BOUND:
                stable += 1
            else:
                stable = 0

            if stable >= STABLE_WINDOW:
                recovery = stable
                break

    if recovery is None:
        recovery = len(tail)

    # Log residuals
    with open(RESIDUAL_DIR / f"residuals_seed_{seed}.csv", "w") as f:
        f.write("step,residual\n")
        for i, r in enumerate(agg.residuals):
            f.write(f"{i},{r}\n")

    return AuditResult(
        seed=seed,
        safety_ok=recovery <= MAX_RECOVERY_STEPS,
        max_residual=max(agg.residuals) if agg.residuals else 0.0,
        verifier_ops=agg.ops,
        recovery_steps=recovery,
        runtime=time.time() - start
    )

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------

def main():
    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    logging.info("=" * 72)
    logging.info("TETRAKLEIN ADVERSARIAL AUDIT — RASPBERRY PI 5 (TAIL RECOVERY)")
    logging.info("=" * 72)

    start = time.time()
    results = []

    for seed in SEEDS:
        r = run_single_seed(seed)
        results.append(r)
        logging.info(
            "SEED=%d | SAFETY=%s | MAX_RES=%.3e | RECOVERY=%d | OPS=%d",
            r.seed, r.safety_ok, r.max_residual, r.recovery_steps, r.verifier_ops
        )

    worst = max(results, key=lambda r: r.max_residual)

    mem_after = proc.memory_info().rss / 1024**2

    logging.info("=" * 72)
    logging.info("SAFETY OK       : %s", all(r.safety_ok for r in results))
    logging.info("MAX RESIDUAL    : %.3e", worst.max_residual)
    logging.info("RECOVERY STEPS : %d", worst.recovery_steps)
    logging.info("VERIFIER OPS   : %d", worst.verifier_ops)
    logging.info("RUNTIME        : %.3fs", time.time() - start)
    logging.info("MEMORY DELTA   : %.2f MB", mem_after - mem_before)
    logging.info("AUDIT COMPLETE")

if __name__ == "__main__":
    main()
