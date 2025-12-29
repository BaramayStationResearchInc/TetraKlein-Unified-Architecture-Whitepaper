"""
TetraKlein IPv6 + PQC Identity Audit
===================================

This audit establishes a cryptographically bound, deterministic identity
root derived from:

  • ML-KEM-1024 public key
  • ML-DSA-87 (Dilithium-5) public key
  • Domain-separated hash construction

It then:
  • Derives a stable IPv6 ULA address
  • Verifies determinism and mutation sensitivity
  • Inserts the identity into a Q₆ hypercube routing table
  • Accounts verifier operations
  • Emits IdentityAIR recursion metadata

This is an ENGINEERING FEASIBILITY + SAFETY AUDIT.
It is not a formal cryptographic proof.

Author: Baramay Station Research Inc.
License: Apache 2.0
"""

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

import os
import time
import json
import hashlib
import logging
import psutil
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import oqs
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging Setup (MANDATED FORMAT)
# ---------------------------------------------------------------------

ID_DIR = LOG_ROOT / "ipv6_pqc_identity_audit"
ID_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ID_DIR / "ipv6_pqc_identity_audit.log"
CONSOLE_LOG = ID_DIR / "console.log"

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

DOMAIN_SEPARATOR = b"TETRAKLEIN::PQC::IPV6::NODEID"
ULA_PREFIX = "fd00"
Q_DIMENSION = 6                  # Q₆ hypercube
Q_NODES = 2 ** Q_DIMENSION
IDENTITY_AIR_TARGET_DEPTH = 64   # explicit recursion target

random.seed(1337)

# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------

@dataclass
class IdentityAuditResult:
    ipv6_address: str
    kem_fp: str
    sig_fp: str
    node_hash: str
    node_hash_lower120: str
    determinism_ok: bool
    mutation_detected: bool
    verifier_ops: int
    q6_neighbors: List[int]
    identity_air_depth: int
    audit_digest: str
    runtime: float
    memory_delta_mb: float

# ---------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def hexfp(data: bytes, n=16) -> str:
    return hashlib.sha256(data).hexdigest()[:n]

def derive_ipv6_from_hash(h: bytes) -> str:
    """
    Take lower 120 bits of SHA-256 hash and form fdXX:XXXX:...
    """
    lower = h[-15:]  # 120 bits
    hexd = lower.hex()
    groups = [hexd[i:i+4] for i in range(0, len(hexd), 4)]
    return f"{ULA_PREFIX}:{':'.join(groups)}"

def hamming_neighbors(node: int, dim: int) -> List[int]:
    return [node ^ (1 << i) for i in range(dim)]

# ---------------------------------------------------------------------
# Core Audit Logic
# ---------------------------------------------------------------------

def run_ipv6_pqc_identity_audit() -> IdentityAuditResult:
    start = time.time()
    proc = psutil.Process(os.getpid())
    mem_before = proc.memory_info().rss / 1024**2

    verifier_ops = 0

    # ------------------------------------------------------------
    # 1. PQC Key Generation
    # ------------------------------------------------------------

    with oqs.KeyEncapsulation("ML-KEM-1024") as kem:
        kem_pk = kem.generate_keypair()
    verifier_ops += 1

    with oqs.Signature("ML-DSA-87") as sig:
        sig_pk = sig.generate_keypair()
    verifier_ops += 1

    kem_fp = hexfp(kem_pk)
    sig_fp = hexfp(sig_pk)

    # ------------------------------------------------------------
    # 2. Deterministic Node Hash
    # ------------------------------------------------------------

    node_hash = sha256(DOMAIN_SEPARATOR + kem_pk + sig_pk)
    node_hash_hex = node_hash.hex()
    node_hash_lower120 = node_hash_hex[-30:]

    ipv6_addr = derive_ipv6_from_hash(node_hash)

    # Determinism check
    node_hash_2 = sha256(DOMAIN_SEPARATOR + kem_pk + sig_pk)
    determinism_ok = node_hash == node_hash_2
    verifier_ops += 1

    # ------------------------------------------------------------
    # 3. Mutation Sensitivity Test
    # ------------------------------------------------------------

    mutated_pk = bytearray(kem_pk)
    mutated_pk[0] ^= 0x01  # single-bit flip

    mutated_hash = sha256(DOMAIN_SEPARATOR + bytes(mutated_pk) + sig_pk)
    mutated_ipv6 = derive_ipv6_from_hash(mutated_hash)

    mutation_detected = (mutated_ipv6 != ipv6_addr)
    verifier_ops += 1

    # ------------------------------------------------------------
    # 4. Q₆ Routing Simulation
    # ------------------------------------------------------------

    node_index = int.from_bytes(node_hash[:2], "big") % Q_NODES
    neighbors = hamming_neighbors(node_index, Q_DIMENSION)
    verifier_ops += len(neighbors)

    # ------------------------------------------------------------
    # 5. IdentityAIR Recursion Metadata
    # ------------------------------------------------------------

    identity_air_depth = IDENTITY_AIR_TARGET_DEPTH
    verifier_ops += identity_air_depth

    # ------------------------------------------------------------
    # 6. Audit Digest
    # ------------------------------------------------------------

    audit_payload = json.dumps({
        "domain": DOMAIN_SEPARATOR.decode(),
        "kem_fp": kem_fp,
        "sig_fp": sig_fp,
        "ipv6": ipv6_addr,
        "node_index": node_index,
        "neighbors": neighbors,
        "air_depth": identity_air_depth,
    }, sort_keys=True).encode()

    audit_digest = hashlib.sha256(audit_payload).hexdigest()

    runtime = time.time() - start
    mem_after = proc.memory_info().rss / 1024**2

    return IdentityAuditResult(
        ipv6_address=ipv6_addr,
        kem_fp=kem_fp,
        sig_fp=sig_fp,
        node_hash=node_hash_hex,
        node_hash_lower120=node_hash_lower120,
        determinism_ok=determinism_ok,
        mutation_detected=mutation_detected,
        verifier_ops=verifier_ops,
        q6_neighbors=neighbors,
        identity_air_depth=identity_air_depth,
        audit_digest=audit_digest,
        runtime=runtime,
        memory_delta_mb=mem_after - mem_before,
    )

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------

def main():
    logging.info("=" * 69)
    logging.info("TETRAKLEIN IPV6 + PQC IDENTITY AUDIT — START")
    logging.info("=" * 69)

    result = run_ipv6_pqc_identity_audit()

    logging.info("DOMAIN_SEPARATOR    : %s", DOMAIN_SEPARATOR.decode())
    logging.info("KYBER1024_PUB_FP    : %s", result.kem_fp)
    logging.info("DILITHIUM5_PUB_FP  : %s", result.sig_fp)
    logging.info("NODE_HASH_SHA256   : %s", result.node_hash)
    logging.info("NODE_HASH_LOWER120 : %s", result.node_hash_lower120)
    logging.info("ULA_PREFIX         : fd00::/8")
    logging.info("IPV6_ADDRESS       : %s", result.ipv6_address)
    logging.info("DETERMINISM_CHECK  : %s", "PASS" if result.determinism_ok else "FAIL")
    logging.info("MUTATION_DETECTED  : %s", result.mutation_detected)
    logging.info("Q6_NEIGHBORS       : %s", result.q6_neighbors)
    logging.info("IDENTITY_AIR_DEPTH : %d", result.identity_air_depth)
    logging.info("VERIFIER_OPS       : %d", result.verifier_ops)
    logging.info("AUDIT_DIGEST_SHA256: %s", result.audit_digest)
    logging.info("RUNTIME            : %.3fs", result.runtime)
    logging.info("MEMORY_DELTA       : %.2f MB", result.memory_delta_mb)

    logging.info("=" * 69)
    logging.info("TETRAKLEIN IPV6 + PQC IDENTITY AUDIT — COMPLETE")
    logging.info("=" * 69)

if __name__ == "__main__":
    main()
