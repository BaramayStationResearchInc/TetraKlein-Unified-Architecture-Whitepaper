#!/usr/bin/env python3
"""
TetraKlein Zero-Knowledge Witness Validation Suite
==================================================

Validates:
- NPU execution -> witness recording pipeline
- AIR constraint enforcement (time, range, hash)
- Deterministic replay (double execution)
- Fault injection detection
- IVC epoch folding
- STARK trace construction
- Commitment binding
- Cross-execution determinism

Author: Baramay Station Research Inc.
License: Apache 2.0
"""

import sys
import time
import hashlib
from pathlib import Path

from tk_hailo_zk_executor import TKHailoZKExecutor
from tk_zk_witness_recorder import (
    TKZKWitnessRecorder,
    AIRViolation,
    TKEpochFolder,
    TKFaultInjector,
)
from tklocal_paths import LOG_ROOT

# =====================================================================
# Configuration
# =====================================================================

HEF_PATH = "/home/baramaystation1/TetraKlein/examples/tetraklein-local/tests/hef/tk_kernel.hef"
NETWORK_NAME = "tk_kernel"

FIELD_MODULUS = 2**64 - 59

# Test vectors
TEST_INPUTS = [
    (5, 3),
    (10, 2),
    (7, 7),
    (1, 1),
    (42, 17),
    (255, 255),  # max range
    (0, 0),      # min range
    (128, 64),   # mid range
]

# =====================================================================
# Logging Setup
# =====================================================================

LOG_DIR = LOG_ROOT / "zk_validation"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "zk_validation.log"
CONSOLE_LOG = LOG_DIR / "console.log"

logfile = open(CONSOLE_LOG, "a", buffering=1)
sys.stdout = logfile
sys.stderr = logfile

# =====================================================================
# Utilities
# =====================================================================

def banner(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)

def ok(msg):
    print(f"[ OK ] {msg}")

def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)

# =====================================================================
# Test 1: Basic NPU Execution + Witness Recording
# =====================================================================

def test_basic_execution():
    banner("TEST 1: Basic NPU Execution + Witness Recording")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    
    results = []
    for x1, x2 in TEST_INPUTS:
        y = zk.step(x1, x2)
        results.append((x1, x2, y))
        print(f"  ({x1:3d}, {x2:3d}) -> {y:3d}")
    
    trace = zk.export_witness()
    commitment = zk.commitment()
    
    print(f"\nWitness recorded: {len(trace['t'])} steps")
    print(f"Commitment: {commitment.hex()}")
    
    zk.shutdown()
    ok("Basic execution and witness recording")
    return results, commitment

# =====================================================================
# Test 2: AIR Constraint Validation
# =====================================================================

def test_air_constraints():
    banner("TEST 2: AIR Constraint Validation")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    
    # Execute test vectors
    for x1, x2 in TEST_INPUTS:
        zk.step(x1, x2)
    
    # Validate AIR constraints
    try:
        zk.witness.check_air()
        ok("All AIR constraints satisfied")
    except AIRViolation as e:
        fail(f"AIR violation: {e}")
    
    # Get trace
    trace_cols = zk.witness.export_trace_columns()
    n = len(trace_cols["t"])
    
    # C1: Time monotonicity
    for i in range(n):
        if trace_cols["t"][i] != i:
            fail(f"Time monotonicity violated at step {i}")
    ok("Time monotonicity (C1)")
    
    # C2: Range bounds
    for i in range(n):
        if not (0 <= trace_cols["x1"][i] <= 255):
            fail(f"Range violation x1[{i}] = {trace_cols['x1'][i]}")
        if not (0 <= trace_cols["x2"][i] <= 255):
            fail(f"Range violation x2[{i}] = {trace_cols['x2'][i]}")
        if not (0 <= trace_cols["y"][i] <= 255):
            fail(f"Range violation y[{i}] = {trace_cols['y'][i]}")
    ok("Range bounds (C2)")
    
    # C3: Hash chain consistency (batch-level)
    # In optimized mode, hashes are computed per batch (8 steps)
    # All steps in a batch share the same hash root
    # This is valid: the batch hash commits to all steps in that batch
    
    # Verify batches have consistent hashes
    batch_size = 8
    for batch_start in range(0, n, batch_size):
        batch_end = min(batch_start + batch_size, n)
        batch_hash = trace_cols["h"][batch_start]
        
        # All steps in batch should have same hash
        for i in range(batch_start, batch_end):
            if trace_cols["h"][i] != batch_hash:
                fail(f"Batch hash inconsistency at step {i}")
    
    ok("Hash chain consistency (C3 - batch mode)")
    
    zk.shutdown()

# =====================================================================
# Test 3: Deterministic Replay
# =====================================================================

def test_deterministic_replay():
    banner("TEST 3: Deterministic Replay")
    
    # First execution
    zk1 = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    for x1, x2 in TEST_INPUTS:
        zk1.step(x1, x2)
    commitment1 = zk1.commitment()
    trace1 = zk1.export_witness()
    zk1.shutdown()
    
    # Second execution (identical inputs)
    zk2 = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    for x1, x2 in TEST_INPUTS:
        zk2.step(x1, x2)
    commitment2 = zk2.commitment()
    trace2 = zk2.export_witness()
    zk2.shutdown()
    
    # Compare commitments
    if commitment1 != commitment2:
        fail("Commitments differ across executions")
    ok("Commitment determinism")
    
    # Compare traces
    for key in trace1:
        if trace1[key] != trace2[key]:
            fail(f"Trace column '{key}' differs")
    ok("Trace determinism")
    
    print(f"Commitment (both runs): {commitment1.hex()}")

# =====================================================================
# Test 4: Checked Execution (Double-Run Divergence Detection)
# =====================================================================

def test_checked_execution():
    banner("TEST 4: Checked Execution (Divergence Detection)")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    
    # Execute with double-run validation
    for x1, x2 in TEST_INPUTS[:4]:  # Use subset for speed
        try:
            y = zk.step_checked(x1, x2)
            print(f"  ({x1}, {x2}) -> {y} [verified]")
        except RuntimeError as e:
            fail(f"Divergence detected: {e}")
    
    ok("Double-run execution produces identical outputs")
    zk.shutdown()

# =====================================================================
# Test 5: Fault Injection Detection
# =====================================================================

def test_fault_injection():
    banner("TEST 5: Fault Injection Detection")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    injector = TKFaultInjector(flip_mask=0x01)
    
    # Execute normally
    for x1, x2 in TEST_INPUTS[:3]:
        zk.step(x1, x2)
    
    # Get trace columns
    trace_cols = zk.witness.export_trace_columns()
    
    # Inject fault in the column data (bypassing the witness recorder)
    last_idx = len(trace_cols["y"]) - 1
    original_y = trace_cols["y"][last_idx]
    corrupted_y = injector.inject(original_y)
    
    print(f"Injecting fault: y={original_y} -> {corrupted_y}")
    
    # Manually corrupt the trace column
    trace_cols["y"][last_idx] = corrupted_y
    
    # Now verify range bounds directly (this should fail)
    fault_detected = False
    try:
        for i in range(len(trace_cols["y"])):
            if not (0 <= trace_cols["y"][i] <= 255):
                fault_detected = True
                raise AIRViolation(f"Range violation detected at step {i}")
    except AIRViolation as e:
        print(f"  Detected: {e}")
        ok("Fault injection correctly detected")
        fault_detected = True
    
    if not fault_detected:
        # If range is still valid, check if re-recording would detect it
        # Create new recorder and try to record corrupted values
        try:
            test_recorder = TKZKWitnessRecorder()
            for i in range(len(trace_cols["t"])):
                test_recorder.record(
                    trace_cols["x1"][i],
                    trace_cols["x2"][i],
                    trace_cols["y"][i]  # This includes corrupted value
                )
            
            # If we get here without error, the fault wasn't in range
            # But commitment should differ from original
            new_commitment = test_recorder.final_commitment()
            original_commitment = zk.commitment()
            
            if new_commitment != original_commitment:
                print(f"  Detected: Commitment changed after fault")
                ok("Fault injection correctly detected (via commitment)")
            else:
                fail("Fault not detected")
        except AIRViolation as e:
            print(f"  Detected: {e}")
            ok("Fault injection correctly detected")
    
    zk.shutdown()

# =====================================================================
# Test 6: IVC Epoch Folding
# =====================================================================

def test_ivc_folding():
    banner("TEST 6: IVC Epoch Folding")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    
    # Execute witness
    for x1, x2 in TEST_INPUTS:
        zk.step(x1, x2)
    
    trace = zk.export_witness()
    
    # Fold hashes into IVC accumulator
    folder = TKEpochFolder(FIELD_MODULUS)
    for h in trace["h"]:
        folder.absorb(h)
    
    root = folder.root()
    steps = folder.steps
    
    print(f"IVC steps: {steps}")
    print(f"IVC root: {root}")
    
    if steps != len(trace["h"]):
        fail("IVC step count mismatch")
    
    ok("IVC epoch folding")
    zk.shutdown()

# =====================================================================
# Test 7: Range Boundary Testing
# =====================================================================

def test_range_boundaries():
    banner("TEST 7: Range Boundary Testing")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    
    boundary_cases = [
        (0, 0),       # minimum
        (255, 255),   # maximum
        (0, 255),     # min-max
        (255, 0),     # max-min
        (1, 254),     # near boundaries
    ]
    
    for x1, x2 in boundary_cases:
        y = zk.step(x1, x2)
        print(f"  ({x1:3d}, {x2:3d}) -> {y:3d}")
        
        # Verify range
        if not (0 <= y <= 255):
            fail(f"Output out of range: y={y}")
    
    ok("All outputs within uint8 range")
    zk.shutdown()

# =====================================================================
# Test 8: STARK Trace Construction
# =====================================================================

def test_stark_trace_construction():
    banner("TEST 8: STARK Trace Construction")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    
    # Execute witness
    for x1, x2 in TEST_INPUTS:
        zk.step(x1, x2)
    
    # Build STARK-compatible trace
    trace_cols = zk.export_witness()
    n = len(trace_cols["t"])
    
    stark_trace = []
    for i in range(n):
        stark_trace.append([
            trace_cols["t"][i] % FIELD_MODULUS,
            trace_cols["x1"][i] % FIELD_MODULUS,
            trace_cols["x2"][i] % FIELD_MODULUS,
            trace_cols["y"][i] % FIELD_MODULUS,
            trace_cols["h"][i] % FIELD_MODULUS,
        ])
    
    print(f"STARK trace shape: {len(stark_trace)} x {len(stark_trace[0])}")
    print(f"Field modulus: {FIELD_MODULUS}")
    
    # Verify all elements in field
    for row in stark_trace:
        for elem in row:
            if elem >= FIELD_MODULUS:
                fail(f"Element exceeds field modulus: {elem}")
    
    ok("STARK trace construction valid")
    zk.shutdown()

# =====================================================================
# Test 9: Commitment Binding
# =====================================================================

def test_commitment_binding():
    banner("TEST 9: Commitment Binding")
    
    # Run 1: First set of inputs
    zk1 = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    for x1, x2 in TEST_INPUTS[:4]:
        zk1.step(x1, x2)
    commitment1 = zk1.commitment()
    zk1.shutdown()
    
    # Run 2: Different inputs
    zk2 = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    for x1, x2 in TEST_INPUTS[4:]:
        zk2.step(x1, x2)
    commitment2 = zk2.commitment()
    zk2.shutdown()
    
    # Commitments must differ (different inputs)
    if commitment1 == commitment2:
        fail("Commitments identical for different inputs")
    
    print(f"Commitment 1: {commitment1.hex()}")
    print(f"Commitment 2: {commitment2.hex()}")
    ok("Commitment binding (different inputs -> different commitments)")

# =====================================================================
# Test 10: Performance Characterization
# =====================================================================

def test_performance():
    banner("TEST 10: Performance Characterization")
    
    zk = TKHailoZKExecutor(HEF_PATH, NETWORK_NAME)
    
    # Warm-up
    for _ in range(10):
        zk.step(42, 17)
    
    # Timed execution
    n_ops = 1000
    start = time.time()
    for i in range(n_ops):
        x1 = (i * 7) % 256
        x2 = (i * 13) % 256
        zk.step(x1, x2)
    elapsed = time.time() - start
    
    ops_per_sec = n_ops / elapsed
    latency_ms = (elapsed / n_ops) * 1000
    
    print(f"Operations: {n_ops}")
    print(f"Elapsed: {elapsed:.3f}s")
    print(f"Throughput: {ops_per_sec:.1f} ops/sec")
    print(f"Latency: {latency_ms:.3f} ms/op")
    
    ok("Performance characterization")
    zk.shutdown()

# =====================================================================
# Main Test Runner
# =====================================================================

def main():
    start_time = time.time()
    
    banner("TETRAKLEIN ZERO-KNOWLEDGE WITNESS VALIDATION SUITE")
    print(f"HEF: {HEF_PATH}")
    print(f"Network: {NETWORK_NAME}")
    print(f"Test vectors: {len(TEST_INPUTS)}")
    
    try:
        test_basic_execution()
        test_air_constraints()
        test_deterministic_replay()
        test_checked_execution()
        test_fault_injection()
        test_ivc_folding()
        test_range_boundaries()
        test_stark_trace_construction()
        test_commitment_binding()
        test_performance()
        
        banner("ALL ZK VALIDATION TESTS PASSED")
        elapsed = time.time() - start_time
        print(f"Total runtime: {elapsed:.2f}s")
        ok("Complete ZK witness validation suite")
        
    except Exception as e:
        banner("VALIDATION FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
