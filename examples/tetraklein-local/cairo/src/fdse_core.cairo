// src/fdse_core.cairo
// Full Dive Safety Envelope core logic (AIR-friendly, integer-only)

use core::felt252;
use core::integer::{u32, u128};

// ----------------------------
// FDSE constants
// ----------------------------

pub const MAX_FAILS: u32 = 3;

// Judge polarity
pub const FDSE_SAFE: felt252 = 1;
pub const FDSE_HARD_FAIL: felt252 = 0;

// Integer slack for discrete Lyapunov contraction
pub const FDSE_EPSILON: u128 = 5_u128;

// ----------------------------
// Lyapunov function (integer)
// V = E_lin + E_ang + neural^2
// ----------------------------
pub fn lyapunov_value_int(
    e_lin: u128,
    e_ang: u128,
    neural_load: u128
) -> u128 {
    e_lin + e_ang + neural_load * neural_load
}

// ----------------------------
// FDSE judge
// Returns:
//   1 → SAFE
//   0 → HARD_FAIL
// ----------------------------
pub fn fdse_judge_int(
    v0: u128,
    v1: u128,
    lambda_scaled: u128,
    scale: u128
) -> felt252 {
    let lhs: u128 = v1 * scale;
    let rhs: u128 = lambda_scaled * v0;

    // SAFE if contraction holds with epsilon slack
    if lhs <= rhs + FDSE_EPSILON {
        FDSE_SAFE
    } else {
        FDSE_HARD_FAIL
    }
}

// ----------------------------
// FDSE fail automaton
// ----------------------------
pub fn fdse_fail_automaton(
    fail_count: u32,
    judge: felt252
) -> (u32, felt252) {
    // SAFE → reset counter
    if judge == FDSE_SAFE {
        return (0_u32, 0);
    }

    // HARD_FAIL → increment
    let new_fail: u32 = fail_count + 1_u32;

    if new_fail >= MAX_FAILS {
        return (new_fail, 1); // white-room
    }

    (new_fail, 0)
}
