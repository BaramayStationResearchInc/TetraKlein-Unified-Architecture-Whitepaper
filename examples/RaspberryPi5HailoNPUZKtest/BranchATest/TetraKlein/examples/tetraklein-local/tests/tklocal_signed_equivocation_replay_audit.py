"""
TetraKlein Signed Equivocation + Replay Audit
=============================================

Detects:
  • Signed equivocation (same epoch, different signed state)
  • Replay attacks (same signed frame reappears after delay)

Model:
  • Post-quantum signatures (ML-DSA-87 / Dilithium-5)
  • Asynchronous gossip with bounded delay
  • Deterministic replay detection

This is NOT a cryptographic proof.
This IS a system-level safety audit suitable for IdentityAIR.
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import os
import time
import random
import logging
import psutil
import hashlib
from dataclasses import dataclass
from typing import Dict, Set, Tuple, List

import oqs
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------

AUDIT_DIR = LOG_ROOT / "signed_equivocation_replay_audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = AUDIT_DIR / "signed_equivocation_replay_audit.log"
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
# Configuration
# ---------------------------------------------------------------------

EPOCHS = 64
MAX_DELAY = 8
REPLAY_EPOCH_GAP = 10

random.seed(1337)

# ---------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class SignedFrame:
    epoch: int
    state: float
    signature: bytes

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def canonical_message(epoch: int, state: float) -> bytes:
    """
    Canonical serialization for signing / verification.
    """
    return f"{epoch}:{state:.12f}".encode()

# ---------------------------------------------------------------------
# Audit Runner
# ---------------------------------------------------------------------

def run_signed_equivocation_replay_audit():
    start = time.time()
    proc = psutil.Process(os.getpid())
    mem0 = proc.memory_info().rss / 1024**2

    verifier_ops = 0

    # --- Identity (real PQC signatures) ---
    signer = oqs.Signature("ML-DSA-87")
    pubkey = signer.generate_keypair()
    verifier = oqs.Signature("ML-DSA-87")

    # --- Tracking ---
    seen_frames: Set[Tuple[int, float, bytes]] = set()
    seen_epochs: Dict[int, float] = {}
    signed_history: Dict[int, SignedFrame] = {}
    inbox: List[Tuple[SignedFrame, int]] = []

    equivocation_detected = False
    replay_detected = False
    detection_epoch = None

    # --- System state ---
    state = 1.0

    for epoch in range(EPOCHS):
        # Deterministic contractive evolution
        state *= 0.9

        # --- Honest signed frame ---
        msg = canonical_message(epoch, state)
        sig = signer.sign(msg)
        frame = SignedFrame(epoch, state, sig)
        signed_history[epoch] = frame

        inbox.append((frame, random.randint(0, MAX_DELAY)))
        verifier_ops += 1

        # --- Inject signed equivocation ---
        if epoch == 12:
            forged_state = state + 0.5
            forged_msg = canonical_message(epoch, forged_state)
            forged_sig = signer.sign(forged_msg)
            inbox.append(
                (SignedFrame(epoch, forged_state, forged_sig),
                 random.randint(0, MAX_DELAY))
            )

        # --- Inject TRUE replay (exact same signed frame) ---
        if epoch == 20:
            replay_epoch = epoch - REPLAY_EPOCH_GAP
            replay_frame = signed_history[replay_epoch]
            inbox.append(
                (replay_frame, random.randint(0, MAX_DELAY))
            )

        # --- Delivery phase ---
        next_inbox = []
        for f, delay in inbox:
            if delay > 0:
                next_inbox.append((f, delay - 1))
                continue

            verifier_ops += 1
            msg = canonical_message(f.epoch, f.state)

            # Signature verification
            if not verifier.verify(msg, f.signature, pubkey):
                raise RuntimeError("SIGNATURE VERIFICATION FAILURE")

            frame_id = (f.epoch, f.state, f.signature)

            # Replay detection
            if frame_id in seen_frames:
                replay_detected = True
                continue

            # Signed equivocation detection
            if f.epoch in seen_epochs and seen_epochs[f.epoch] != f.state:
                equivocation_detected = True
                detection_epoch = epoch
                continue

            # Accept frame
            seen_frames.add(frame_id)
            seen_epochs[f.epoch] = f.state

        inbox = next_inbox

    runtime = time.time() - start
    mem1 = proc.memory_info().rss / 1024**2

    # --- Hard safety assertions ---
    if not equivocation_detected:
        raise RuntimeError("SIGNED EQUIVOCATION NOT DETECTED")

    if not replay_detected:
        raise RuntimeError("REPLAY NOT DETECTED")

    return {
        "equivocation_detected": equivocation_detected,
        "replay_detected": replay_detected,
        "detection_epoch": detection_epoch,
        "verifier_ops": verifier_ops,
        "runtime": runtime,
        "memory_delta": mem1 - mem0,
    }

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------

def main():
    logging.info("=" * 68)
    logging.info("TETRAKLEIN SIGNED EQUIVOCATION + REPLAY AUDIT — START")
    logging.info("=" * 68)

    result = run_signed_equivocation_replay_audit()

    logging.info("EQUIVOCATION DETECTED : %s", result["equivocation_detected"])
    logging.info("REPLAY DETECTED       : %s", result["replay_detected"])
    logging.info("DETECTION EPOCH       : %s", result["detection_epoch"])
    logging.info("VERIFIER OPS          : %d", result["verifier_ops"])
    logging.info("RUNTIME               : %.3fs", result["runtime"])
    logging.info("MEMORY DELTA          : %.2f MB", result["memory_delta"])

    logging.info("=" * 68)
    logging.info("TETRAKLEIN SIGNED EQUIVOCATION + REPLAY AUDIT — COMPLETE")
    logging.info("=" * 68)

if __name__ == "__main__":
    main()
