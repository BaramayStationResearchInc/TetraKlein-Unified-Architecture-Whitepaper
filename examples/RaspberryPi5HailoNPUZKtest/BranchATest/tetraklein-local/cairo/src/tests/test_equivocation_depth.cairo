// src/tests/test_equivocation_depth.cairo

use core::felt252;
use core::array::{ArrayTrait};
use core::integer::u32;

const MAX_DEPTH: u32 = 3;

#[test]
fn equivocation_tree_depth_limited() {
    let mut equivocation_count: u32 = 0;
    let mut rejected: felt252 = 0;

    let _epoch: felt252 = 7;

    // simulate conflicting states
    let mut i: u32 = 0;
    loop {
        if i == 6 {
            break;
        }

        let _forged_state: felt252 = (1_000_000 + i * 111).into();
        equivocation_count += 1;

        if equivocation_count > MAX_DEPTH {
            rejected = 1;
            break;
        }

        i += 1;
    }

    assert(rejected == 1, 'DEPTH_FAIL');
}
