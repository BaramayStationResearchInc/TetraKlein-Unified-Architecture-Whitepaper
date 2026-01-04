use crate::fdse::fdse_judge;

const SCALE: felt252 = 100;
const LAMBDA: felt252 = 95;

#[test]
fn fdse_safe_case() {
    let judge = fdse_judge(10, 9, LAMBDA, SCALE);
    assert(judge == 1, 'expected SAFE');
}

#[test]
fn fdse_unsafe_case() {
    let judge = fdse_judge(10, 12, LAMBDA, SCALE);
    assert(judge == 0, 'expected HARD_FAIL');
}

#[test]
fn fdse_zero_delta() {
    let judge = fdse_judge(10, 10, LAMBDA, SCALE);
    assert(judge == 1, 'expected SAFE');
}
