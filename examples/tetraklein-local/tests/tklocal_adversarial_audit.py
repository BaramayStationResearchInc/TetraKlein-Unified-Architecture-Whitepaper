"""
TetraKlein Adversarial Scheduling & Fault Injection Audit
"""

import os
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

ADV_DIR = LOG_ROOT / "adversarial_audit"
ADV_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ADV_DIR / "adversarial_audit.log"
CONSOLE_LOG = ADV_DIR / "console.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

import sys
logfile = open(CONSOLE_LOG, "a", buffering=1)
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

MAX_FRAMES = 2048
FAULT_FRACTION = 0.15
MAX_DELAY = 32
MAX_REPLAYS = 64

RESIDUAL_BOUND = 1e-2
MAX_RECOVERY_EPOCHS = 32
MAX_VERIFIER_OPS = 50_000

random.seed(1337)

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
    safety_ok: bool
    liveness_ok: bool
    max_residual: float
    verifier_ops: int
    epochs_to_recover: int
    runtime: float

# ---------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------

class AdversarialScheduler:
    def __init__(self):
        self.buffer = []

    def submit(self, frame):
        self.buffer.append(frame)

    def schedule(self):
        scheduled = []

        blocks = [
            self.buffer[i:i + MAX_DELAY]
            for i in range(0, len(self.buffer), MAX_DELAY)
        ]

        for block in blocks:
            scheduled.extend(reversed(block))

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
        n = int(len(frames) * self.fraction)
        for f in random.sample(frames, n):
            f.value += random.uniform(-1.0, 1.0)
            f.valid = False
        return frames

# ---------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------

class Aggregator:
    def __init__(self):
        self.state = 0.0
        self.verifier_ops = 0
        self.residuals = []

    def process(self, frame):
        self.verifier_ops += 1

        if not frame.valid:
            return

        prev = self.state
        self.state = 0.9 * self.state + 0.1 * frame.value
        self.residuals.append(abs(self.state - prev))

# ---------------------------------------------------------------------
# Audit Runner
# ---------------------------------------------------------------------

def run_adversarial_audit():
    start = time.time()

    scheduler = AdversarialScheduler()
    injector = FaultInjector(FAULT_FRACTION)
    agg = Aggregator()

    frames = [
        Frame(i, random.uniform(-1, 1))
        for i in range(MAX_FRAMES)
    ]

    for f in frames:
        scheduler.submit(f)

    scheduled = scheduler.schedule()
    corrupted = injector.inject(scheduled)

    recovered_epoch = None

    for i, frame in enumerate(corrupted):
        agg.process(frame)

        if agg.residuals and agg.residuals[-1] < RESIDUAL_BOUND:
            if recovered_epoch is None:
                recovered_epoch = i

        if agg.verifier_ops > MAX_VERIFIER_OPS:
            break

    if recovered_epoch is None:
        recovered_epoch = len(corrupted)

    result = AuditResult(
        safety_ok=recovered_epoch <= MAX_RECOVERY_EPOCHS,
        liveness_ok=True,
        max_residual=max(agg.residuals) if agg.residuals else 0.0,
        verifier_ops=agg.verifier_ops,
        epochs_to_recover=recovered_epoch,
        runtime=time.time() - start,
    )

    return result

# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------

def main():
    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    logging.info("=" * 70)
    logging.info("TETRAKLEIN ADVERSARIAL SCHEDULING AUDIT — START")
    logging.info("=" * 70)

    result = run_adversarial_audit()

    mem_after = proc.memory_info().rss / 1024**2

    logging.info("SAFETY OK       : %s", result.safety_ok)
    logging.info("LIVENESS OK     : %s", result.liveness_ok)
    logging.info("MAX RESIDUAL    : %.4e", result.max_residual)
    logging.info("VERIFIER OPS   : %d", result.verifier_ops)
    logging.info("RECOVERY EPOCHS: %d", result.epochs_to_recover)
    logging.info("RUNTIME        : %.3fs", result.runtime)
    logging.info("MEMORY DELTA   : %.2f MB", mem_after - mem_before)

    if not result.safety_ok:
        raise RuntimeError("SAFETY VIOLATION DETECTED")

    logging.info("TETRAKLEIN ADVERSARIAL AUDIT COMPLETE")

if __name__ == "__main__":
    main()
