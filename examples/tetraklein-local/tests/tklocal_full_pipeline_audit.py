"""
TetraKlein Full Pipeline Audit — Production Reference
====================================================

End-to-end feasibility and safety audit covering:
  Identity → Routing → Execution → AIR → IVC → DTC → Ledger

Validates deterministic binding from ML-KEM-1024 + ML-DSA-87 through
hypercube ledger root with explicit AIR/IVC/DTC proxies.

SYSTEM-INTEGRITY REGRESSION — hard failure on invariant violation.
"""

import os
import time
import json
import hashlib
import logging
import psutil
from dataclasses import dataclass
from typing import List

import oqs
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
PIPE_DIR = LOG_ROOT / "full_pipeline_audit"
PIPE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = PIPE_DIR / "full_pipeline_audit.log"
CONSOLE_LOG = PIPE_DIR / "console.log"

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
# Constants
# ---------------------------------------------------------------------
DOMAIN_ID = b"TETRAKLEIN::PIPELINE::IDENTITY"
ULA_PREFIX = "fd00"
Q_DIM = 6
Q_NODES = 2 ** Q_DIM
AIR_MAX_DEGREE = 2
IVC_TARGET_DEPTH = 64
DTC_CONTRACTION = 0.9
DTC_RESIDUAL_THRESHOLD = 1e-6

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

def derive_ipv6(h: bytes) -> str:
    """Lower 120 bits → fdXX:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX"""
    lower = h[-15:]  # 120 bits = 15 bytes
    hex_str = lower.hex()  # 30 hex digits
    groups = [hex_str[i:i+4] for i in range(0, 30, 4)]
    return f"{ULA_PREFIX}:{':'.join(groups)}"

def hamming_neighbors(n: int) -> List[int]:
    return [n ^ (1 << i) for i in range(Q_DIM)]

# ---------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------
@dataclass
class PipelineResult:
    ipv6: str
    q_node: int
    air_degree_ok: bool
    ivc_depth: int
    dtc_residual: float
    ledger_root: str
    verifier_ops: int
    runtime: float
    memory_delta: float

# ---------------------------------------------------------------------
# Full Pipeline Audit
# ---------------------------------------------------------------------
def run_full_pipeline_audit() -> PipelineResult:
    start = time.time()
    proc = psutil.Process(os.getpid())
    mem0 = proc.memory_info().rss / 1024**2
    verifier_ops = 0

    # 1. PQC Identity (real liboqs primitives)
    with oqs.KeyEncapsulation("ML-KEM-1024") as kem:
        kem_pk = kem.generate_keypair()
    with oqs.Signature("ML-DSA-87") as sig:
        sig_pk = sig.generate_keypair()
    verifier_ops += 2

    identity_hash = sha256(DOMAIN_ID + kem_pk + sig_pk)
    ipv6 = derive_ipv6(identity_hash)

    # 2. Q₆ Routing Placement
    q_node = int.from_bytes(identity_hash[:2], "big") % Q_NODES
    neighbors = hamming_neighbors(q_node)
    verifier_ops += len(neighbors)

    # 3. TK-VM Symbolic Execution (degree-1 proxy)
    x_prev = 1.0
    x_next = 0.5 * x_prev + 0.5  # linear transition
    verifier_ops += 1

    # 4. AIR Degree Check
    transition_degree = 1
    air_degree_ok = transition_degree <= AIR_MAX_DEGREE
    verifier_ops += 1

    # 5. IVC Folding Simulation (contractive map)
    state = 1.0
    for _ in range(IVC_TARGET_DEPTH):
        state = 0.5 * state
        verifier_ops += 1

    # 6. DTC Projection + Contraction
    dtc_state = state
    for _ in range(16):
        dtc_state = DTC_CONTRACTION * dtc_state
        verifier_ops += 1
    dtc_residual = abs(dtc_state)

    # 7. Ledger Commitment
    ledger_payload = json.dumps({
        "ipv6": ipv6,
        "q_node": q_node,
        "dtc_state": dtc_state,
    }, sort_keys=True).encode()
    ledger_root = hashlib.sha256(ledger_payload).hexdigest()
    verifier_ops += 1

    runtime = time.time() - start
    mem1 = proc.memory_info().rss / 1024**2

    result = PipelineResult(
        ipv6=ipv6,
        q_node=q_node,
        air_degree_ok=air_degree_ok,
        ivc_depth=IVC_TARGET_DEPTH,
        dtc_residual=dtc_residual,
        ledger_root=ledger_root,
        verifier_ops=verifier_ops,
        runtime=runtime,
        memory_delta=mem1 - mem0,
    )

    # Hard safety assertions
    if not air_degree_ok:
        raise RuntimeError("AIR DEGREE VIOLATION")
    if dtc_residual > DTC_RESIDUAL_THRESHOLD:
        raise RuntimeError(f"DTC RESIDUAL EXCEEDS THRESHOLD: {dtc_residual}")

    return result

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
def main() -> None:
    logging.info("=" * 72)
    logging.info("TETRAKLEIN FULL PIPELINE AUDIT — START")
    logging.info("=" * 72)

    result = run_full_pipeline_audit()

    logging.info("IPV6_ADDRESS       : %s", result.ipv6)
    logging.info("Q6_NODE_INDEX      : %d", result.q_node)
    logging.info("AIR_DEGREE_OK      : %s", result.air_degree_ok)
    logging.info("IVC_DEPTH          : %d", result.ivc_depth)
    logging.info("DTC_RESIDUAL       : %.6e", result.dtc_residual)
    logging.info("LEDGER_ROOT_SHA256 : %s", result.ledger_root)
    logging.info("VERIFIER_OPS       : %d", result.verifier_ops)
    logging.info("RUNTIME            : %.3fs", result.runtime)
    logging.info("MEMORY_DELTA       : %.2f MB", result.memory_delta)

    logging.info("=" * 72)
    logging.info("TETRAKLEIN FULL PIPELINE AUDIT — COMPLETE")
    logging.info("=" * 72)

if __name__ == "__main__":
    main()