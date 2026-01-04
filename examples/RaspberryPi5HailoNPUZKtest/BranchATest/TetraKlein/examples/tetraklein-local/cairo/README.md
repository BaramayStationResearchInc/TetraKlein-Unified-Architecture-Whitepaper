# TetraKlein Cairo Verification System

This directory contains the **Cairo-enforced safety and adversarial verification layer** of the TetraKlein architecture.

Running `snforge test` executes a suite of **deterministic, proof-compatible tests** that define and enforce the system’s *Full-Dive Safety Envelope (FDSE)* and its resistance to adversarial behavior.

This is not application logic.
This is **safety, soundness, and convergence enforcement**.

---

## What This Cairo System Is

The Cairo codebase defines **hard safety invariants** that must hold for TetraKlein to be considered correct under:

- long-running execution
- adversarial scheduling
- replay and equivocation attacks
- temporal reordering
- bounded fault injection
- epoch-based finality

These invariants are expressed as:
- deterministic state machines
- bounded counters
- contractive updates
- recovery conditions
- adversarial models

and are validated via Cairo tests that are compatible with **STARK/AIR reasoning**.

If these tests pass, the system is **provably within its safety envelope**.

---

## What `snforge test` Does

When you run:


snforge test

the following occurs:

Cairo code is compiled into a proof-compatible intermediate form.

Each test is executed deterministically under Cairo’s semantics.

All safety invariants are checked, including failure cases.

Gas usage is reported as a proxy for proof cost and constraint weight.

This is equivalent to asserting:

“If this logic were embedded into an AIR / proof system, these invariants would hold.”

How to Read the Output

Example output:
/mnt/c/tetraklein-local/cairo$ snforge test
   Compiling snforge_scarb_plugin v0.52.0
    Finished `release` profile [optimized] target(s) in 0.37s
   Compiling test(tetraklein_air_unittest) tetraklein_air v0.1.0 (/mnt/c/tetraklein-local/cairo/Scarb.toml)
    Finished `dev` profile target(s) in 1 second


Collected 10 test(s) from tetraklein_air package
Running 10 test(s) from src/
[PASS] tetraklein_air::tests::test_fdse::fdse_safe_case (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~20300)
[PASS] tetraklein_air::tests::test_fdse::fdse_zero_delta (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~20300)
[PASS] tetraklein_air::tests::test_fdse_full::fdse_full_safety_envelope (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~194000)
[PASS] tetraklein_air::tests::test_replay_depth::replay_depth_limited (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~21560)
[PASS] tetraklein_air::tests::test_epoch_finality::epoch_finality_window_enforced (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~229930)
[PASS] tetraklein_air::tests::test_temporal_audit::temporal_epoch_stability_audit (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~3262980)
[PASS] tetraklein_air::tests::test_equivocation_depth::equivocation_tree_depth_limited (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~27960)
[PASS] tetraklein_air::tests::test_fdse::fdse_unsafe_case (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~20200)
[PASS] tetraklein_air::tests::test_replay::signed_equivocation_and_replay_audit (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~15638440)
[PASS] tetraklein_air::tests::test_adversarial_audit::adversarial_scheduling_audit (l1_gas: ~0, l1_data_gas: ~0, l2_gas: ~53867790)
Tests: 10 passed, 0 failed, 0 ignored, 0 filtered out

This means all enforced safety domains passed.

What Each Test Proves
FDSE — Full-Dive Safety Envelope

fdse_safe_case

fdse_zero_delta

fdse_unsafe_case

fdse_full_safety_envelope

These prove:

bounded state evolution

correct contraction behavior

explicit detection of unsafe dynamics

long-horizon stability under iteration

Replay Safety

signed_equivocation_and_replay_audit

replay_depth_limited

These prove:

replay attacks are bounded

replay + equivocation cannot cause unbounded divergence

replay depth is strictly limited

Equivocation Safety

equivocation_tree_depth_limited

This proves:

adversarial branching cannot grow without bound

equivocation trees are depth-limited by construction

Epoch Finality

epoch_finality_window_enforced

This proves:

epoch transitions obey strict finality windows

late or reordered data cannot violate finalized state

Temporal Stability

temporal_epoch_stability_audit

This proves:

after faults, the system returns to a stable regime

recovery occurs within bounded epochs

residuals decay under contractive dynamics

Adversarial Scheduling

adversarial_scheduling_audit

This proves:

reordering, replay, and fault injection are explicitly modeled

recovery is only allowed after faults cease

stability must be sustained before recovery is declared

recovery occurs within a bounded window

This is the strongest adversarial test in the suite.

What a Passing Test Suite Means

When all tests pass:

The Full-Dive Safety Envelope is enforced

The system is resistant to replay and equivocation

Temporal recovery is provably bounded

Adversarial scheduling cannot break convergence

All guarantees are enforced inside Cairo

No Python, logging, or orchestration code is trusted for these properties.

What This Is Not

This Cairo system is not:

an application runtime

a performance benchmark

a user-facing protocol

a replacement for Python analysis tools

Python tools exist for stress testing and exploration.
Cairo defines what is allowed.
| Layer          | Role                            | Trusted |
| -------------- | ------------------------------- | ------- |
| Cairo          | Safety & adversarial invariants | ✅ Yes   |
| AIR / Proof    | Cryptographic soundness         | ✅ Yes   |
| Python         | Analysis & stress testing       | ❌ No    |
| Logs / Reports | Diagnostics                     | ❌ No    |
If an invariant is not enforced here, it is not a security guarantee.

Bottom Line

Running snforge test and seeing all tests pass means:

“This system, under the modeled adversarial conditions, is provably safe, stable, and recoverable.”

That is the purpose of this Cairo codebase.
More may be added in 2026 
