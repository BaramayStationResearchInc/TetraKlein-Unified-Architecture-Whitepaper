\# TetraKlein Local Validation Suite



Status: Validation Test

Audience: Technical auditors, external reviewers

Scope: Computational feasibility and cryptographic soundness checks

Not a production system



\### Purpose of This Test Suite



This contains a local, reproducible validation suite for the TetraKlein execution and proof model.

The goal is not to demonstrate a complete system or a deployable product.

This validation does not attempt to model malicious provers, adaptive adversaries, or cryptographic side-channel attacks.



\### The goal is to answer a narrower and critical question:



Can the proposed execution, proof, and aggregation model actually run on real hardware under conservative assumptions?



This suite provides evidence that it can.



\### What This Validation Demonstrates



This validation demonstrates:



Deterministic execution trace generation



STARK-compatible Algebraic Intermediate Representation (AIR) constraints



The validation assumes a standard FRI-based STARK soundness model with conservative parameter bounds; no novel soundness claims are made.

FRI domain sizing and blow-up feasibility



FRI query soundness versus verifier cost



Incremental Verifiable Computation (IVC) recursion bounds



IVC is used here in the generic sense of recursive proof aggregation, not as a claim of compatibility with any specific named IVC construction



Prover throughput and energy feasibility on consumer GPUs



Epoch-based aggregation suitable for real-time workloads



All tests are executed on standard consumer hardware with no specialized accelerators.



\### What This Validation Does Not Claim



This does not claim:



Production readiness



Regulatory or medical approval



Completeness of the full TetraKlein system



Optimized performance ceilings



Security against all adversarial models



Hardware independence



It establishes feasibility, not deployment.



Hardware \& Software Assumptions



\### Tested Hardware



GPU: NVIDIA GeForce RTX 2070 SUPER (8 GB VRAM)



CPU: AMD Ryzen 7 3700X (8-Core)



RAM: 64 GB DDR4



Software Environment



Python 3.12



CUDA 12.x (forward compatible runtime)



cupy-cuda12x



numba



sympy



\### Test Structure



tetraklein-local/

│

├─ env/

│  ├─ system.env

│  ├─ compute.env

│  ├─ crypto.env

│  ├─ xr.env

│  ├─ safety.env

│  ├─ paths.env

│  └─ versions.lock

│

├─ tests/

│  ├─ tklocal\_validate.py

│  ├─ tklocal\_stark\_trace.py

│  ├─ tklocal\_fri\_domain.py

│  ├─ tklocal\_ivc\_recursion.py

│  ├─ tklocal\_fri\_query\_budget.py

│  ├─ tklocal\_prover\_budget.py

│  ├─ tklocal\_epoch\_aggregation.py

│  ├─ tklocal\_summary\_report.py

│  └─ save\_env\_snapshot.py

│

├─ logs/

│  └─ LATEST/

│     ├─ console.log

│     └─ env\_snapshot.json

│

└─ README.md



\### How to Run the Validation



Environment Setup



Step 1 - Create and activate a virtual environment



python -m venv tklocal-env

source tklocal-env/bin/activate



Install dependencies



pip install numpy sympy cupy-cuda12x



(or equivalent on Windows / WSL)



Step 2 — Run the Full Validation Chain



From the repository root:



python tests/tklocal\_validate.py

python tests/tklocal\_stark\_trace.py

python tests/tklocal\_fri\_domain.py

python tests/tklocal\_ivc\_recursion.py

python tests/tklocal\_fri\_query\_budget.py

python tests/tklocal\_prover\_budget.py

python tests/tklocal\_epoch\_aggregation.py

python tests/tklocal\_summary\_report.py

python tests/save\_env\_snapshot.py



All output is automatically written to:



logs/LATEST/console.log



Step 3 — Capture the Environment Snapshot



Run once after validation:



python tests/save\_env\_snapshot.py



Logging \& Provenance



Canonical Log Location



All logs are written to:



tetraklein-local/logs/LATEST/



This directory is the single source of truth for a validation run.



Contents



console.log

Complete stdout/stderr from all tests



env\_snapshot.json

Timestamped hardware + software environment



OS / kernel



Python version



CUDA runtime



GPU model



NVIDIA driver version



Logs are deterministic in structure and content order; numerical timing values may vary slightly across runs.



\### How to Audit the Results



An auditor or reviewer should:



Inspect env\_snapshot.json to confirm hardware and runtime



Review console.log from top to bottom



Verify that all sections conclude with \[ OK ]



Confirm no silent failures or skipped checks



Optionally re-run the suite on equivalent hardware



No proprietary tools are required.



\### Interpretation Guidance



If all tests pass:



The execution model is computationally feasible



Proof generation and verification are bounded



Aggregation amortizes costs effectively



No exponential blow-ups are observed



Real-time workloads are plausible under conservative assumptions



\### If a test fails:



The failure is explicit



The script exits immediately



The failure location is recorded in the logs



Intended Use of These Results



These results are intended for:



Technical review



Feasibility assessment



External expert audit



Informing future research directions



They are not marketing claims.



\### What Each Test Verifies



tklocal\_validate.py



CUDA availability



GPU stability



Basic contractivity and numerical sanity



tklocal\_stark\_trace.py



Trace allocation



AIR transition degree limits



Trace evolution determinism



Folding behavior



tklocal\_fri\_domain.py



Domain sizing vs blow-up factor



Folding depth bounds



GPU allocation feasibility



tklocal\_ivc\_recursion.py



Incremental verifiable computation recursion depth



Verifier state growth



Logarithmic scaling behavior



tklocal\_fri\_query\_budget.py



Query count vs soundness



Verifier cost scaling



tklocal\_prover\_budget.py



Prover throughput



Energy per proof



Real-time feasibility for batching



tklocal\_epoch\_aggregation.py



Epoch-level amortization behavior



tklocal\_summary\_report.py



Consolidated human-readable report



save\_env\_snapshot.py



Records system, GPU, CUDA, Python, and environment metadata



Produces env\_snapshot.json for audit traceability



\### Contact / Attribution



Principal Systems Architect

Advanced Systems Directorate

Baramay Station Research Inc.

Michael Tass MacDonald Dec 14 2025 AD



\### Final Statement



Known Limitations



Single-node only



No network latency modeling



No adversarial prover simulation



No production cryptographic hardening



No formal security proof included



These are intentional exclusions for a local feasibility study.



\### License \& Disclaimer



This is provided for research and engineering evaluation only.



It does not represent:



A production cryptographic system



A deployed network



A certified security product



Use at your own risk.



\### Final Note



This validation demonstrates that proof-carrying execution with modern cryptographic constraints is computationally viable on today’s hardware.



Nothing more is claimed.



Every claim made here is backed by code, hardware, and logs.



Nothing relies on assumption alone.

