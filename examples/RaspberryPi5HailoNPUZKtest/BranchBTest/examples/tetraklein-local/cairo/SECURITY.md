# SECURITY.md

## TetraKlein Security Model & Trust Boundaries

This document defines the security guarantees, enforcement layers, and trust assumptions of the TetraKlein system. It explicitly delineates what is *cryptographically enforced* inside Cairo/AIR versus what is *analytical or operational* in Python tooling.

---

## 1. Core Principle

**All safety-critical invariants that affect proof validity, state soundness, or adversarial resistance are enforced in Cairo.**

Python is *not* a trusted execution environment for safety.
Python exists only for:
- analysis
- stress testing
- design-time validation
- reporting

Any failure that would invalidate system safety **must be detectable and enforced inside Cairo**.

---

## 2. FDSE — Full-Dive Safety Envelope

The **Full-Dive Safety Envelope (FDSE)** defines the complete set of invariants required for safe, stable, and adversarial-resistant operation of TetraKlein in long-running, real-time, or XR-grade execution.

FDSE is **fully enforced in Cairo**.

FDSE guarantees include:
- bounded state evolution
- contractive convergence
- recovery after faults
- resistance to replay and equivocation
- epoch finality under adversarial scheduling

No FDSE property relies on Python for enforcement.

---

## 3. Cairo-Enforced Security Invariants

The following properties are **provably enforced in Cairo** via tests and AIR-compatible logic.

### 3.1 State Convergence & Stability
- FDSE zero-delta behavior
- FDSE safe and unsafe regimes
- Long-horizon stability under bounded inputs

Modules:
- `test_fdse`
- `test_fdse_full`

---

### 3.2 Replay Resistance
- Bounded replay depth
- Detection of signed equivocation with replay
- Replay cannot cause unbounded divergence

Modules:
- `test_replay`
- `test_replay_depth`

---

### 3.3 Equivocation Resistance
- Equivocation tree depth is bounded
- Adversarial branching cannot grow unbounded

Modules:
- `test_equivocation_depth`

---

### 3.4 Epoch Finality
- Epoch transitions obey a strict finality window
- No late or adversarial reordering can violate finality guarantees

Modules:
- `test_epoch_finality`

---

### 3.5 Temporal Recovery
- System recovers to stable operation after faults
- Recovery must occur within bounded epochs
- Residual decay is enforced

Modules:
- `test_temporal_audit`

---

### 3.6 Adversarial Scheduling
- Reordering, replay, and fault injection are explicitly modeled
- Recovery is enforced only after fault cessation
- Sustained stability is required before declaring recovery

Modules:
- `test_adversarial_audit`

---

## 4. Python Tooling (Non-Trusted)

Python scripts **do not enforce security invariants**.
They are used for:

- deep stress testing
- adversarial scenario exploration
- capacity planning
- budget estimation
- reporting and visualization

Failures in Python **cannot** compromise proof soundness.

Examples include:
- `tklocal_deep_audit.py`
- `tklocal_full_pipeline_audit.py`
- `tklocal_mega_coupled_stress_audit.py`
- `tklocal_summary_report.py`
- `tklocal_fri_*`
- `tklocal_prover_budget.py`

These tools may reveal *design weaknesses*, but they do not define correctness.

---

## 5. Trust Boundary Summary

| Layer  | Trusted for Safety | Role |
|------|-------------------|------|
| Cairo | ✅ Yes | Enforces all FDSE and adversarial invariants |
| AIR / Proof | ✅ Yes | Cryptographic soundness |
| Python | ❌ No | Analysis, stress testing, reporting |
| Logs / Reports | ❌ No | Diagnostics only |

If an invariant is not enforced in Cairo, it is **not** a security guarantee.

---

## 6. Security Scope Statement

TetraKlein guarantees:
- safety under bounded adversarial behavior
- recovery after faults
- resistance to replay, equivocation, and reordering
- long-running temporal stability

TetraKlein does **not** claim:
- protection against unbounded resource exhaustion
- availability guarantees outside defined verifier limits
- correctness of external orchestration or infrastructure

---

## 7. Responsible Disclosure

Security issues affecting Cairo-enforced invariants should be reported privately to the maintainers.

Issues limited to Python tooling, performance, or reporting are considered non-critical.

---

## 8. Final Note

**FDSE is the Full-Dive Safety Envelope.  
FDSE is fully enforced in Cairo.  
Python is advisory only.**

This boundary is intentional, explicit, and final.
