use core::integer::{u32, u128};
use core::array::ArrayTrait;

// ------------------------------------------------------------
// Constants
// ------------------------------------------------------------
const MAX_FRAMES: u32 = 2048;
const MAX_DELAY: u32 = 32;
const MAX_REPLAYS: u32 = 64;

const FAULT_NUM: u32 = 15;
const FAULT_DEN: u32 = 100;

const MAX_VERIFIER_OPS: u32 = 50_000;
const MAX_RECOVERY_EPOCHS: u32 = 128;

// sustained-recovery requirement
const STABLE_WINDOW: u32 = 4;

const SCALE: u128 = 100;
const ALPHA: u128 = 90;
const BETA:  u128 = 10;
const RESIDUAL_BOUND: u128 = 10;

// ------------------------------------------------------------
// Copy-safe frame
// ------------------------------------------------------------
#[derive(Copy, Drop)]
struct Frame {
    index: u32,
    value: u128,
    valid: u32,
    stale: u32,
}

// ------------------------------------------------------------
// Deterministic pseudo-noise (Cairo-safe widening)
// ------------------------------------------------------------
fn pseudo_value(i: u32) -> u128 {
    let x: u32 = (i * 97 + 13) % 200;
    let xu: u128 = x.into();
    xu
}

// ------------------------------------------------------------
// Test
// ------------------------------------------------------------
#[test]
fn adversarial_scheduling_audit() {
    let mut frames: Array<Frame> = ArrayTrait::new();

    // --------------------------------------------------------
    // Frame generation
    // --------------------------------------------------------
    let mut i: u32 = 0;
    loop {
        if i == MAX_FRAMES {
            break;
        }

        frames.append(Frame {
            index: i,
            value: pseudo_value(i),
            valid: 1,
            stale: 0,
        });

        i += 1;
    }

    // --------------------------------------------------------
    // Adversarial pipeline (single-pass)
    // --------------------------------------------------------
    let mut state: u128 = 0;
    let mut verifier_ops: u32 = 0;

    // sentinel = not yet recovered
    let mut recovery_epoch: u32 = MAX_FRAMES + 1;
    let mut stable_count: u32 = 0;

    let fault_limit: u32 = (frames.len() * FAULT_NUM) / FAULT_DEN;

    let mut idx: u32 = 0;
    loop {
        if idx >= frames.len() || verifier_ops > MAX_VERIFIER_OPS {
            break;
        }

        // ----------------------------
        // Adversarial reordering
        // ----------------------------
        let block_base = (idx / MAX_DELAY) * MAX_DELAY;
        let offset = MAX_DELAY - 1 - (idx % MAX_DELAY);

        let read_idx =
            if block_base + offset < frames.len() {
                block_base + offset
            } else {
                idx
            };

        let mut f: Frame = *frames.at(read_idx);

        // ----------------------------
        // Replay injection
        // ----------------------------
        if idx < MAX_REPLAYS {
            f.stale = 1;
        }

        // ----------------------------
        // Fault injection
        // ----------------------------
        if idx < fault_limit {
            f.value = f.value + 100_u128;
            f.valid = 0;
        }

        verifier_ops += 1;

        // ----------------------------
        // Aggregation + recovery logic
        // ----------------------------
        if f.valid == 1 {
            let prev = state;
            state = (ALPHA * state + BETA * f.value) / SCALE;

            let residual =
                if state > prev { state - prev } else { prev - state };

            // Recovery can only begin AFTER faults stop
            if idx >= fault_limit {
                if residual < RESIDUAL_BOUND {
                    stable_count += 1;

                    if stable_count >= STABLE_WINDOW
                        && recovery_epoch == MAX_FRAMES + 1
                    {
                        recovery_epoch = idx;
                    }
                } else {
                    stable_count = 0;
                }
            } else {
                // faults active → cannot accumulate stability
                stable_count = 0;
            }
        }

        idx += 1;
    }

    // --------------------------------------------------------
    // Assertions
    // --------------------------------------------------------
    assert(verifier_ops <= MAX_VERIFIER_OPS, 'VERIFIER_LIMIT');

    // Measure recovery latency relative to end of fault window
    assert(
        recovery_epoch - fault_limit <= MAX_RECOVERY_EPOCHS,
        'RECOVERY_TOO_SLOW'
    );
}
