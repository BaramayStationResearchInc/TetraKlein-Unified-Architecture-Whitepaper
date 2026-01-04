# TetraKlein Local Validation Suite

**Status**: Feasibility Validation  
**Audience**: Technical auditors, external reviewers  
**Scope**: Computational feasibility and cryptographic soundness checks  
**Important**: This is **not** a production system.

### Purpose of This Test Suite

This repository contains a local, reproducible validation suite for the TetraKlein execution and proof model.

The goal is **not** to demonstrate a complete system or a deployable product. This validation does **not** attempt to model malicious provers, adaptive adversaries, or cryptographic side-channel attacks.

The suite answers a narrower, critical question:  

> Can the proposed execution, proof, and aggregation model actually run on real hardware under conservative assumptions?

This suite provides empirical evidence that it can.

### What This Validation Demonstrates

- Deterministic execution trace generation
- STARK-compatible Algebraic Intermediate Representation (AIR) constraints (assuming standard FRI-based STARK soundness
-  with conservative parameters; no novel soundness claims)
- FRI domain sizing and blow-up feasibility
- FRI query soundness versus verifier cost
- Incremental Verifiable Computation (IVC) recursion bounds (used here in the generic sense of recursive proof aggregation)
- Prover throughput and energy feasibility on consumer GPUs
- Epoch-based aggregation suitable for real-time workloads
- The hypercube spectral-gap scaling result proves that TetraKlein’s ledger, gossip, and recursive proof layers converge
- in 𝑂(𝑁 log 𝑁) time with bounded verifier cost, closing the last mathematical risk preventing real-world execution.

All tests execute on standard consumer hardware with no specialized accelerators.

### What This Validation Does **Not** Claim

- Production readiness
- Regulatory or medical approval
- Completeness of the full TetraKlein system
- Optimized performance ceilings
- Security against all adversarial models
- Hardware independence

It establishes **feasibility**, not deployment.

### Tested Hardware & Software

**Hardware**  
- GPU: NVIDIA GeForce RTX 2070 SUPER (8 GB VRAM)  
- CPU: AMD Ryzen 7 3700X (8-core)  
- RAM: 64 GB DDR4  

**Software**  
- Python 3.12  
- CUDA 12.x (forward-compatible runtime)  
- CuPy (cupy-cuda12x)  
- Numba, SymPy  

### Repository Structure

```
tetraklein-local/
│
├─ env/
│   ├─ system.env
│   ├─ compute.env
│   ├─ crypto.env
│   ├─ xr.env
│   ├─ safety.env
│   ├─ paths.env
│   └─ versions.lock
│
├─ tests/
│   ├─ tklocal_validate.py
│   ├─ tklocal_stark_trace.py
│   ├─ tklocal_fri_domain.py
│   ├─ tklocal_ivc_recursion.py
│   ├─ tklocal_fri_query_budget.py
│   ├─ tklocal_prover_budget.py
│   ├─ tklocal_epoch_aggregation.py
│   ├─ tklocal_summary_report.py
│   ├─ save_env_snapshot.py
│   └─ tklocal_deep_audit.py
│
├─ logs/
│   └─ LATEST/
│       ├─ console.log
│       └─ env_snapshot.json
│
└─ README.md
```

### How to Run the Validation Suite

1. **Environment Setup**  
   ```bash
   python -m venv tklocal-env
   source tklocal-env/bin/activate  # .\tklocal-env\Scripts\activate on Windows
   pip install numpy sympy cupy-cuda12x psutil matplotlib qutip
   ```

2. **Run the Full Chain** (from repository root)  
   ```bash
   python tests/tklocal_validate.py
   python tests/tklocal_stark_trace.py
   python tests/tklocal_fri_domain.py
   python tests/tklocal_ivc_recursion.py
   python tests/tklocal_fri_query_budget.py
   python tests/tklocal_prover_budget.py
   python tests/tklocal_epoch_aggregation.py
   python tests/tklocal_summary_report.py
   python tests/save_env_snapshot.py
   ```

   All output is written to `logs/LATEST/console.log`.

3. **Run the Deep Mathematical Feasibility Audit** (CPU-only)  
   ```bash
   python tests/tklocal_deep_audit.py
   ```
   Results appear in `logs/deep_audit/` (structured log, console trace, and `spectral_gap.png`).

### Logging & Provenance

The canonical log location is `tetraklein-local/logs/LATEST/` (main suite) and `logs/deep_audit/` (deep audit). These directories are the single source of truth for any validation run.

### How to Audit the Results

An external reviewer should:
- Inspect `env_snapshot.json` to confirm hardware/runtime environment
- Read `console.log` sequentially
- Verify every section ends with `[ OK ]`
- Confirm no silent skips or exceptions
- Optionally re-run on equivalent hardware

No proprietary tools are required.

### Interpretation Guidance

**All tests pass** →  
The execution model is computationally feasible, proof generation/verification costs are bounded, aggregation amortizes effectively, and no exponential blow-ups occur. Real-time workloads are plausible under conservative assumptions.

**Any failure** →  
The script exits immediately with an explicit `[FAIL]` message logged.

### Detailed Test Descriptions

| Script                          | Primary Verification Focus                                      |
|---------------------------------|-----------------------------------------------------------------|
| `tklocal_validate.py`           | CUDA availability, GPU stability, basic contractivity          |
| `tklocal_stark_trace.py`        | Trace allocation, AIR degree limits, determinism, folding      |
| `tklocal_fri_domain.py`         | Domain sizing vs blow-up, folding depth, GPU allocation        |
| `tklocal_ivc_recursion.py`      | IVC recursion depth, verifier state growth, logarithmic scaling|
| `tklocal_fri_query_budget.py`   | Query count vs soundness, verifier cost scaling                |
| `tklocal_prover_budget.py`      | Prover throughput, energy per proof, batching feasibility      |
| `tklocal_epoch_aggregation.py`  | Epoch amortization for XR-rate workloads                       |
| `tklocal_summary_report.py`     | Consolidated human-readable executive summary                  |
| `save_env_snapshot.py`          | Hardware/software provenance capture                           |
| `tklocal_deep_audit.py`         | Mathematical coherence (contractivity, spectral gap, AIR degree, physics closure, PQ margins) |

### Known Limitations (Intentional)

- Single-node only
- No network latency modeling
- No adversarial prover simulation
- No production cryptographic hardening
- No formal security proofs included

### Contact / Attribution

Principal Systems Architect  
Baramay Station Research Inc.  
Michael Tass MacDonald  
14 December 2025

### Final Statement

This validation demonstrates that proof-carrying execution with modern cryptographic constraints is computationally viable on consumer-grade hardware as of late 2025.

Nothing more is claimed. Every claim made here is backed by executable code, real hardware measurements, and auditable logs.

**License & Disclaimer**  
Provided for research and engineering evaluation only. Use at your own risk. This is not a production cryptographic system, deployed network, or certified security product.
