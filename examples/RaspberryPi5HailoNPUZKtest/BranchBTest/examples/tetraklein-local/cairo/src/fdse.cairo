use core::felt252;
use core::integer::u256;
use core::traits::TryInto;

/// FDSE Lyapunov Judge
/// Returns:
///   1 = SAFE
///   0 = HARD_FAIL
///
/// SAFE iff:
///   (1) v1 == v0            (no expansion)
///   OR
///   (2) λ*v0 >= v1*S        (Lyapunov contraction)
pub fn fdse_judge(
    v0: felt252,
    v1: felt252,
    lambda_scaled: felt252,
    scale: felt252
) -> felt252 {

    // Special-case: no change → SAFE
    if v1 == v0 {
        return 1;
    }

    // Compute both sides separately (NO subtraction in field)
    let lhs_felt: felt252 = lambda_scaled * v0;
    let rhs_felt: felt252 = v1 * scale;

    // Convert to ordered integers
    let lhs: u256 = lhs_felt.try_into().unwrap();
    let rhs: u256 = rhs_felt.try_into().unwrap();

    // Lyapunov condition
    if lhs >= rhs {
        1
    } else {
        0
    }
}
