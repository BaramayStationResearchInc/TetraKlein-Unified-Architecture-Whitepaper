// src/tests/test_replay.cairo
// TetraKlein Signed Equivocation + Replay Audit (Cairo)
// System-level safety audit (non-cryptographic)

use core::felt252;
use core::array::{ArrayTrait};
use core::integer::u32;

const EPOCHS: u32 = 64;
const MAX_DELAY: u32 = 8;
const REPLAY_EPOCH_GAP: u32 = 10;

// Deterministic symbolic "signature"
fn symbolic_signature(epoch: felt252, state: felt252) -> felt252 {
    epoch * 1_000_000 + state
}

#[test]
fn signed_equivocation_and_replay_audit() {
    // -----------------------------
    // Tracking state
    // -----------------------------
    let mut seen_epochs: Array<(felt252, felt252)> = ArrayTrait::new();
    let mut seen_frames: Array<(felt252, felt252, felt252)> = ArrayTrait::new();

    let mut inbox_frames: Array<(felt252, felt252, felt252)> = ArrayTrait::new();
    let mut inbox_delays: Array<u32> = ArrayTrait::new();

    let mut history_states: Array<felt252> = ArrayTrait::new();
    let mut history_sigs: Array<felt252> = ArrayTrait::new();

    let mut equivocation_detected: felt252 = 0;
    let mut replay_detected: felt252 = 0;

    // -----------------------------
    // System state (INTEGER ONLY)
    // -----------------------------
    let mut state: u32 = 1_000_000;

    // -----------------------------
    // Epoch loop
    // -----------------------------
    let mut epoch: u32 = 0;
    loop {
        if epoch == EPOCHS {
            break;
        }

        // Deterministic contraction (legal integer arithmetic)
        state = state * 9 / 10;

        let epoch_felt: felt252 = epoch.into();
        let state_felt: felt252 = state.into();
        let sig = symbolic_signature(epoch_felt, state_felt);

        history_states.append(state_felt);
        history_sigs.append(sig);

        inbox_frames.append((epoch_felt, state_felt, sig));
        inbox_delays.append(epoch % MAX_DELAY);

        // -----------------------------
        // Inject signed equivocation
        // -----------------------------
        if epoch == 12 {
            let forged_state: u32 = state + 500_000;
            let forged_state_felt: felt252 = forged_state.into();
            let forged_sig = symbolic_signature(epoch_felt, forged_state_felt);

            inbox_frames.append((epoch_felt, forged_state_felt, forged_sig));
            inbox_delays.append((epoch + 3) % MAX_DELAY);
        }

        // -----------------------------
        // Inject TRUE replay
        // -----------------------------
        if epoch == 20 {
            let replay_epoch: u32 = epoch - REPLAY_EPOCH_GAP;

            let re_state = *history_states[replay_epoch];
            let re_sig = *history_sigs[replay_epoch];

            inbox_frames.append((replay_epoch.into(), re_state, re_sig));
            inbox_delays.append((epoch + 5) % MAX_DELAY);
        }

        // -----------------------------
        // Delivery phase
        // -----------------------------
        let mut next_frames: Array<(felt252, felt252, felt252)> = ArrayTrait::new();
        let mut next_delays: Array<u32> = ArrayTrait::new();

        let mut i: u32 = 0;
        loop {
            if i == inbox_frames.len() {
                break;
            }

            let delay = *inbox_delays[i];
            let (ep_ref, st_ref, sg_ref) = inbox_frames[i];

            let f_epoch = *ep_ref;
            let f_state = *st_ref;
            let f_sig = *sg_ref;

            if delay > 0 {
                next_frames.append((f_epoch, f_state, f_sig));
                next_delays.append(delay - 1);
                i += 1;
                continue;
            }

            // -----------------------------
            // Replay detection
            // -----------------------------
            let mut j: u32 = 0;
            loop {
                if j == seen_frames.len() {
                    break;
                }
                let (se, ss, sg) = seen_frames[j];
                if *se == f_epoch && *ss == f_state && *sg == f_sig {
                    replay_detected = 1;
                    break;
                }
                j += 1;
            }

            // -----------------------------
            // Signed equivocation detection
            // -----------------------------
            let mut k: u32 = 0;
            loop {
                if k == seen_epochs.len() {
                    break;
                }
                let (ep, st) = seen_epochs[k];
                if *ep == f_epoch && *st != f_state {
                    equivocation_detected = 1;
                    break;
                }
                k += 1;
            }

            // Accept frame
            seen_frames.append((f_epoch, f_state, f_sig));
            seen_epochs.append((f_epoch, f_state));

            i += 1;
        }

        inbox_frames = next_frames;
        inbox_delays = next_delays;

        epoch += 1;
    }

    // -----------------------------
    // Hard safety assertions
    // -----------------------------
    assert(equivocation_detected == 1, 0);
	assert(replay_detected == 1, 0);
}
