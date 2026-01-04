# TetraKlein: Post-Quantum Verifiable Simulation Stack

## Project Overview
TetraKlein is a research-grade architecture integrating **Post-Quantum Cryptography (PQC)**, **ZK-STARK systems**, and **Real-time AI Inference** on edge hardware. This repository contains the Epoch 0 baseline for a self-authenticating mesh identity system anchored on a Raspberry Pi 5.

## Technical Architecture
The stack operates across three primary layers:
1.  **Inference Layer:** Real-time physics/digital-twin simulation accelerated by the **Hailo-8L NPU**.
2.  **Witness Bridge:** A high-throughput **Rust** pipeline (Rayon + Memmap2) that extracts NPU telemetry into a 3-byte delta-encoded format.
3.  **Verification Layer:** A **Cairo 2 (STARK)** prover that validates the integrity of the simulation trace (up to 50,000 steps).



## System DNA (Reference Environment)
To ensure reproducibility, the following environment was used for the initial 50k step lock:
- **Hardware:** Raspberry Pi 5 (8GB) + Hailo-8L M.2 HAT
- **NPU Firmware:** 4.23.0 (Control Protocol v2)
- **ZK-VM:** Cairo 2 / Scarb 2.8.x / Starknet Foundry
- **PQC Core:** liboqs (Kyber-768 / Dilithium-3)

## Data Specification
The witness data (`.tkbin`) uses a high-density 3-byte stride:
- `Byte 0`: $\Delta X_1$ (Spatial Delta)
- `Byte 1`: $\Delta X_2$ (Temporal Delta)
- `Byte 2`: $Y$ (Witness Value / State Root)

## Performance Benchmarks (Epoch 0)
Validated on Raspberry Pi 5 (Cortex-A76 @ 2.4GHz) using `taskset` affinity:

| Metric | Result | Constraint |
| :--- | :--- | :--- |
| **Throughput** | 11,778,475.3 ops/sec | 4-Core Aggregate |
| **Latency** | 0.1 µs | Per Operation |
| **XR Capacity** | 98,153 ops/frame | @ 120Hz |
| **NPU Efficiency** | 41,482% | Relative to NPU Streaming |

**Commitment Hash:** `eea73de4d83d9e58ffaee5ea93b7b151...`  
**IVC Epoch Root:** `0x18d1ed0212859bff...`

## Deployment Instructions
run

baramaystation1@raspberrypi:~/TetraKlein/examples/tetraklein-local/tests $ cd
baramaystation1@raspberrypi:~ $ cd /home/baramaystation1/TetraKlein/examples/tetraklein-local/tests/
baramaystation1@raspberrypi:~/TetraKlein/examples/tetraklein-local/tests $ taskset -c 0-3 python3 test_optimized_performance.py 10000000
================================================================================
TETRAKLEIN ZK WITNESS RECORDER PERFORMANCE BENCHMARK
================================================================================
Operations      : 10,000,000
Cores           : 4 (A76 multiprocessing)
Mode            : STREAMING (Phase 4)

Results
----------------------------------------
Total time      : 0.849 s
Throughput      : 11,778,475.3 ops/sec (4-core aggregate)
Latency (per op): 0.000 ms | 0.1 µs
Commitment      : eea73de4d83d9e58ffaee5ea93b7b151...
IVC epoch root  : 0x18d1ed0212859bff...

NPU Hardware Comparison
----------------------------------------
NPU streaming   : 28,394 ops/sec
ZK recording    : 11,778,475.3 ops/sec
Efficiency      : 41482.8% of NPU

XR Real-Time Budget (Operations per Frame)
----------------------------------------
60 Hz  : 196,307 ops/frame (16.67 ms budget)
90 Hz  : 130,871 ops/frame (11.11 ms budget)
120 Hz : 98,153 ops/frame ( 8.33 ms budget)

================================================================================
BENCHMARK COMPLETE
================================================================================



### 1. Witness Extraction

/home/baramaystation1/TetraKlein/examples/tetraklein-local/cairo/tetraklein_stark/rust_bridge
cargo run --release

## 2. STARK Verification

snforge test

# example
bash: /home/baramaystation1/TetraKlein/examples/tetraklein-local/cairo/tetraklein_stark/rust_bridge: Is a directory
    Finished `release` profile [optimized] target(s) in 0.05s
     Running `target/release/rust_bridge`
[+] TetraKlein Stack: 50000 steps processed in 0.003s
   Compiling test(tetraklein_stark_unittest) tetraklein_stark v0.1.0 (/home/baramaystation1/TetraKlein/examples/tetraklein-local/cairo/tetraklein_stark/Scarb.toml)
   Compiling test(tetraklein_stark_integrationtest) tetraklein_stark_integrationtest v0.1.0 (/home/baramaystation1/TetraKlein/examples/tetraklein-local/cairo/tetraklein_stark/Scarb.toml)
    Finished `dev` profile target(s) in 21 seconds


Collected 1 test(s) from tetraklein_stark package
Running 0 test(s) from src/
Running 1 test(s) from tests/
[PASS] tetraklein_stark_integrationtest::test_contract::test_stark_integrity_lock (l1_gas: ~0, l1_data_gas: ~96, l2_gas: ~453340400)
Tests: 1 passed, 0 failed, 0 ignored, 0 filtered out

baramaystation1@raspberrypi:~/TetraKlein/examples/tetraklein-local/cairo/tetraklein_stark/rust_bridge $ 

 

## Verification & Integrity (Provenance Suite)

To guarantee the mathematical lineage of the TetraKlein stack, the following manifests are provided for the Epoch 0 baseline. These files allow any researcher to verify that the local environment and data shards have not drifted from the Baramaystation1 reference state.

### Artifact Directory Map
| File | Purpose |
| :--- | :--- |
| **ARCHITECTURE_MANIFEST_2026-01-03.txt** | The full "System DNA" (Hailo FW 4.23.0, Scarb 2.8.x, Rust, and OQS bindings). |
| **ARCHITECTURE_MANIFEST.sha256** | The cryptographic hash of the DNA record itself. |
| **MANIFEST.sha256** | The master cryptographic seal covering all source code and logic. |
| **CHECKSUMS.txt** | Individual SHA-256 hashes for the 50,000-step `.tkbin` witness data shards. |
| **SHA256_PI.txt** | The native hardware-level fingerprint of the Pi 5's deployment state. |

### How to Verify the Integrity
To ensure your local copy of the manifold matches the Baramaystation1 research baseline, run:
```bash
# 1. Verify the source code and logic
sha256sum -c MANIFEST.sha256

# 2. Verify the 10M-step witness shards
sha256sum -c CHECKSUMS.txt

# 3. Verify the system architecture record
sha256sum -c ARCHITECTURE_MANIFEST.sha256

License
Code: Apache 2.0 | Data: CC BY 4.0

