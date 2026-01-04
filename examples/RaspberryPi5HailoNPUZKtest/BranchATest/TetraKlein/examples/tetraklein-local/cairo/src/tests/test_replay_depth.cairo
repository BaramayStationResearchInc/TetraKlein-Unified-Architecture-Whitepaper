// src/tests/test_replay_depth.cairo

use core::felt252;
use core::array::{ArrayTrait};
use core::integer::u32;

const MAX_REPLAY: u32 = 2;

#[test]
fn replay_depth_limited() {
    let _frame_id: felt252 = 123456789;
    let mut replay_count: u32 = 0;
    let mut rejected: felt252 = 0;

    let mut i: u32 = 0;
    loop {
        if i == 5 {
            break;
        }

        replay_count += 1;

        if replay_count > MAX_REPLAY {
            rejected = 1;
            break;
        }

        i += 1;
    }

    assert(rejected == 1, 'REPLAY_DEPTH');
}
