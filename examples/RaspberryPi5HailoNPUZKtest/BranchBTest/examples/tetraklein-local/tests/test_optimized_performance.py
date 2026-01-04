#!/usr/bin/env python3
"""
TetraKlein ZK Witness Recorder Performance Benchmark (Final Parallel Version)
Integrates Phase-4 streaming toggle, multiprocessing scaling (4-core A76), and XR/NPU comparison.
"""
import time
import sys
import os
import hashlib
from multiprocessing import Pool
from tk_zk_witness_recorder import TKZKWitnessRecorder

def worker_segment(segment):
    start, end = segment
    unique_path = f"witness_part_core_{start}.tkbin"
    recorder = TKZKWitnessRecorder(streaming=True, log_path=unique_path)
    
    # We use 'i' to ensure unique values across the 1B range
    for i in range(start, end):
        # TetraKlein Arithmetic Trace - Must be dependent on the global step 'i'
        x1 = (i * 7) % 256
        x2 = (i * 13) % 256
        y = (x1 + x2) % 256
        
        recorder.record(x1, x2, y)
        
    return recorder.final_commitment(), recorder.get_epoch_root()
    
    

def benchmark_recorder(n_ops: int = 10000):
    """Benchmark witness recorder with Merkle-style commitment merging."""
    use_streaming = n_ops >= 1_000_000
    log_file = "witness_scale.tkbin" if use_streaming else None

    print("=" * 80)
    print("TETRAKLEIN ZK WITNESS RECORDER PERFORMANCE BENCHMARK")
    print("=" * 80)
    print(f"Operations      : {n_ops:,}")
    print(f"Cores           : 4 (A76 multiprocessing)")
    print(f"Mode            : {'STREAMING (Phase 4)' if use_streaming else 'BUFFERED (Phase 3)'}")
    print()

    # Parallel benchmark execution
    num_cores = 4
    chunk = n_ops // num_cores
    remainder = n_ops % num_cores
    segments = []
    offset = 0
    for i in range(num_cores):
        seg_size = chunk + (1 if i < remainder else 0)
        segments.append((offset, offset + seg_size))
        offset += seg_size

    start = time.perf_counter()
    with Pool(num_cores) as p:
        results = p.map(worker_segment, segments)
    elapsed = time.perf_counter() - start

    # --- HRTH MERGE FIX: CONCATENATE & HASH (Merkle Strategy) ---
    # Instead of XOR, we use a digest to prevent zero-cancellation.
    final_commitments = [c for c, _ in results]
    epoch_roots = [r for _, r in results]
    
    # Merge Commitment: SHA256(Part0 || Part1 || Part2 || Part3)
    hasher = hashlib.sha256()
    for partial in final_commitments:
        hasher.update(partial)
    commitment = hasher.digest()
    
    # Merge Root: Summation (Representative of total work across manifold)
    epoch_root = sum(epoch_roots)

    # --- CALCULATE METRICS ---
    fps = n_ops / elapsed
    latency_ms = (elapsed / n_ops) * 1000
    latency_us = latency_ms * 1000

    print("Results")
    print("-" * 40)
    print(f"Total time      : {elapsed:.3f} s")
    print(f"Throughput      : {fps:,.1f} ops/sec (4-core aggregate)")
    print(f"Latency (per op): {latency_ms:.3f} ms | {latency_us:.1f} µs")
    print(f"Commitment      : {commitment.hex()[:32]}...")
    if use_streaming:
        # Use modular arithmetic for the display to keep it readable
        print(f"IVC epoch root  : {hex(epoch_root % (2**256 - 2**32 * 351 + 1))[:18]}...")
    print()
    

    npu_streaming_fps = 28393.61
    efficiency = (fps / npu_streaming_fps) * 100
    print("NPU Hardware Comparison")
    print("-" * 40)
    print(f"NPU streaming   : {npu_streaming_fps:,.0f} ops/sec")
    print(f"ZK recording    : {fps:,.1f} ops/sec")
    print(f"Efficiency      : {efficiency:.1f}% of NPU")
    print()

    targets = {"60 Hz": 60, "90 Hz": 90, "120 Hz": 120}
    print("XR Real-Time Budget (Operations per Frame)")
    print("-" * 40)
    for name, hz in targets.items():
        budget_ms = 1000 / hz
        ops_per_frame = int(fps / hz)
        print(f"{name:6} : {ops_per_frame:6,d} ops/frame ({budget_ms:5.2f} ms budget)")
    print()

    print("=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)

    return fps

if __name__ == "__main__":
    n_ops = 10000
    if len(sys.argv) > 1:
        try:
            n_ops = int(sys.argv[1])
        except ValueError:
            print("Usage: python3 test_optimized_performance.py [n_operations]")
            sys.exit(1)
    benchmark_recorder(n_ops)
