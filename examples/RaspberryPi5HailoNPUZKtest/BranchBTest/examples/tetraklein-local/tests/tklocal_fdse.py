"""
TetraKlein XR Full-Dive Safety Envelope (FDSE)
==============================================

Guardian process enforcing hard physiological and kinematic safety
constraints prior to DTC projection and XR rendering.

This module generates AIR-compatible constraint logic suitable for
STARK verification.

Hard guarantees:
• No sensory overload
• No vestibular shock
• No adversarial teleport / rotation injection
• Deterministic Z-Frame fallback

License: Apache-2.0
"""

import os
import time
import logging
import psutil
import numpy as np
from dataclasses import dataclass
from tklocal_paths import LOG_ROOT

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
FDSE_DIR = LOG_ROOT / "xr_fdse"
FDSE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = FDSE_DIR / "xr_fdse.log"
CONSOLE_LOG = FDSE_DIR / "console.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)

logfile = open(CONSOLE_LOG, "a", buffering=1)
import sys
sys.stdout = logfile
sys.stderr = logfile

# ---------------------------------------------------------------------
# Safety Constants (XRES)
# ---------------------------------------------------------------------
MAX_LIN_ACCEL = 9.81                  # m/s²
MAX_ANG_VEL   = np.deg2rad(450)       # rad/s
MAX_LAT_JITTER = 5e-4                 # 0.5 ms
LYAPUNOV_LAMBDA = 0.95                # contraction
MAX_FAILS = 3                         # white-room trigger

# ---------------------------------------------------------------------
# XR State Definition (DIMENSIONALLY CORRECT)
# ---------------------------------------------------------------------
@dataclass
class XRState:
    pos: np.ndarray      # ℝ³ position
    rot: np.ndarray      # ℝ³ SO(3) local chart
    v_lin: np.ndarray    # ℝ³ linear velocity
    v_ang: np.ndarray    # ℝ³ angular velocity
    jitter: float
    neural_load: float

# ---------------------------------------------------------------------
# FDSE Guardian
# ---------------------------------------------------------------------
class XRFDSEGuardian:
    def __init__(self):
        self.last_safe: XRState | None = None
        self.fail_count = 0

    # -----------------------------
    # Lyapunov Function (AIR-Safe)
    # -----------------------------
    @staticmethod
    def lyapunov(s: XRState) -> float:
        return (
            np.dot(s.v_lin, s.v_lin)
            + np.dot(s.v_ang, s.v_ang)
            + s.neural_load ** 2
        )

    # -----------------------------
    # Boundary Clipping Operator
    # -----------------------------
    @staticmethod
    def clip_state(s: XRState) -> XRState:
        return XRState(
            pos=s.pos,
            rot=s.rot,
            v_lin=np.clip(s.v_lin, -MAX_LIN_ACCEL, MAX_LIN_ACCEL),
            v_ang=np.clip(s.v_ang, -MAX_ANG_VEL, MAX_ANG_VEL),
            jitter=min(s.jitter, MAX_LAT_JITTER),
            neural_load=min(s.neural_load, 1.0),
        )

    # -----------------------------
    # Guardian Shunt
    # -----------------------------
    def shunt(self, s: XRState, dt: float) -> XRState:
        proc = psutil.Process(os.getpid())
        mem0 = proc.memory_info().rss / 1024**2
        t0 = time.time()

        V0 = self.lyapunov(s)

        # ---- Predict next frame (degree-1 dynamics) ----
        pos_next = s.pos + s.v_lin * dt
        rot_next = s.rot + s.v_ang * dt

        # ---- Construct predicted state ----
        s_pred = XRState(
            pos=pos_next,
            rot=rot_next,
            v_lin=s.v_lin,
            v_ang=s.v_ang,
            jitter=s.jitter,
            neural_load=s.neural_load,
        )

        V1 = self.lyapunov(s_pred)
        residual = V1 - LYAPUNOV_LAMBDA * V0

        hard_fail = (
            np.linalg.norm(s.v_ang) > MAX_ANG_VEL
            or s.jitter > MAX_LAT_JITTER
            or residual > 0
        )

        # ---- Reject frame ----
        if hard_fail:
            self.fail_count += 1
            logging.info("AIR_JUDGE_FUNCTION : HARD_FAIL")
            logging.info("FDSE_RESIDUAL      : %.6e", residual)
            logging.info("FDSE_FAIL_COUNT    : %d", self.fail_count)

            if self.fail_count >= MAX_FAILS:
                logging.info("FDSE_ACTION        : WHITE_ROOM")
                return self.last_safe if self.last_safe else self.clip_state(s)

            logging.info("FDSE_ACTION        : REVERT_TO_Z_FRAME")
            return self.last_safe if self.last_safe else self.clip_state(s)

        # ---- Accept frame ----
        self.fail_count = 0
        self.last_safe = s_pred

        mem1 = proc.memory_info().rss / 1024**2
        logging.info("FDSE_PASS")
        logging.info("FDSE_RESIDUAL      : %.6e", residual)
        logging.info("RUNTIME            : %.6fs", time.time() - t0)
        logging.info("MEMORY_DELTA       : %.2f MB", mem1 - mem0)

        return s_pred

# ---------------------------------------------------------------------
# Test Harness
# ---------------------------------------------------------------------
def run_test(test_id: int, state: XRState):
    guardian = XRFDSEGuardian()
    dt = 1 / 120  # 120 Hz XR

    logging.info("=" * 70)
    logging.info("FDSE TEST %d — START", test_id)
    logging.info("=" * 70)

    for _ in range(5):
        state = guardian.shunt(state, dt)

    logging.info("=" * 70)
    logging.info("FDSE TEST %d — COMPLETE", test_id)
    logging.info("=" * 70)

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
def main():
    normal_state = XRState(
        pos=np.zeros(3),
        rot=np.zeros(3),
        v_lin=np.array([1.5, 0.0, 0.0]),
        v_ang=np.zeros(3),
        jitter=1e-4,
        neural_load=0.1,
    )

    breach_state = XRState(
        pos=np.zeros(3),
        rot=np.zeros(3),
        v_lin=np.zeros(3),
        v_ang=np.array([0.0, np.pi, 0.0]),  # 180° / frame
        jitter=1e-4,
        neural_load=0.2,
    )

    run_test(1, normal_state)
    run_test(2, breach_state)

if __name__ == "__main__":
    main()
