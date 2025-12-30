// src/tests/test_fdse_full.cairo
// Full Dive Safety Envelope end-to-end safety test

use core::felt252;
use core::integer::{u32, u128};

use crate::fdse_core::{
    lyapunov_value_int,
    fdse_judge_int,
    fdse_fail_automaton,
    MAX_FAILS
};

const SCALE: u128 = 100;
const LAMBDA_SCALED: u128 = 95; // λ = 0.95

#[test]
fn fdse_full_safety_envelope() {
    // =====================================================
    // NORMAL (SAFE) PATH — TRUE Lyapunov contraction
    // =====================================================

    let mut fail_count: u32 = 0;
    let mut white_room: felt252 = 0;

    // Initial energy components (only used to seed V)
    let e_lin: u128 = 100;
    let e_ang: u128 = 10;
    let neural: u128 = 3;

    // Start from initial Lyapunov value
    let mut v: u128 = lyapunov_value_int(e_lin, e_ang, neural);

    let mut i: u32 = 0;
    loop {
        if i == 8_u32 {
            break;
        }

        let v0: u128 = v;

        // ✅ TRUE FDSE-safe contraction: contract V itself
        v = (v * LAMBDA_SCALED) / SCALE;

        let v1: u128 = v;

        let judge = fdse_judge_int(v0, v1, LAMBDA_SCALED, SCALE);
        let (fc, wr) = fdse_fail_automaton(fail_count, judge);

        fail_count = fc;
        white_room = wr;

        i += 1_u32;
    }

    // Must NOT escalate on valid contraction
    assert(white_room == 0, 'FDSE_OK');

    // =====================================================
    // BREACH PATH — sustained Lyapunov growth
    // =====================================================

    fail_count = 0;
    white_room = 0;

    let e_lin_b: u128 = 50;
    let e_ang_b: u128 = 500;
    let neural_b: u128 = 5;

    let mut vb: u128 = lyapunov_value_int(e_lin_b, e_ang_b, neural_b);

    let mut j: u32 = 0;
    loop {
        if j == MAX_FAILS + 1_u32 {
            break;
        }

        let v0b: u128 = vb;

        // Explicit adversarial growth
        vb = v0b + 10_u128;

        let v1b: u128 = vb;

        let judge_b = fdse_judge_int(v0b, v1b, LAMBDA_SCALED, SCALE);
        let (fc_b, wr_b) = fdse_fail_automaton(fail_count, judge_b);

        fail_count = fc_b;
        white_room = wr_b;

        if white_room == 1 {
            break;
        }

        j += 1_u32;
    }

    // Must escalate under sustained violation
    assert(white_room == 1, 'FDSE_BRK');
}
