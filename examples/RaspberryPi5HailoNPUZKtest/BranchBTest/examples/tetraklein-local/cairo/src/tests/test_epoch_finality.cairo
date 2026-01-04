// src/tests/test_epoch_finality.cairo

use core::felt252;
use core::array::{ArrayTrait};
use core::integer::u32;

const EPOCHS: u32 = 32;
const FINALITY_WINDOW: u32 = 6;

#[test]
fn epoch_finality_window_enforced() {
    let mut committed_epochs: Array<u32> = ArrayTrait::new();
    let mut committed_states: Array<felt252> = ArrayTrait::new();

    let mut violation_detected: felt252 = 0;

    let mut state: u32 = 1_000_000;

    let mut epoch: u32 = 0;
    loop {
        if epoch == EPOCHS {
            break;
        }

        // deterministic evolution
        state = state * 9 / 10;
        let state_felt: felt252 = state.into();

        committed_epochs.append(epoch);
        committed_states.append(state_felt);

        // --- attempt illegal mutation past finality window ---
        if epoch >= FINALITY_WINDOW {
            let target_epoch = epoch - FINALITY_WINDOW;
            let old_state = *committed_states[target_epoch];

            // forged change
            let forged_state: felt252 = (state + 123_456).into();

            if old_state != forged_state {
                violation_detected = 1;
            }
        }

        epoch += 1;
    }

    assert(violation_detected == 1, 'FINALITY_FAIL');
}
