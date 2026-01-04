import hashlib
from typing import List, Dict


# ============================================================
# Exceptions
# ============================================================

class AIRViolation(Exception):
    """Raised when an AIR constraint is violated."""
    pass


# ============================================================
# AIR Polynomial Definitions
# ============================================================

class TKAIRPolynomials:
    """
    AIR constraints expressed as polynomial checks over a finite field.
    """

    def __init__(self, modulus: int):
        self.p = modulus

    def time_transition(self, t_i, t_next):
        return (t_next - (t_i + 1)) % self.p

    def hash_consistency(self, h_i, h_expected):
        return (h_i - h_expected) % self.p

    def range_check(self, v):
        return 0 if 0 <= v <= 255 else 1


# ============================================================
# ZK Witness Recorder
# ============================================================

class TKZKWitnessRecorder:
    """
    Deterministic ZK witness recorder for hardware-executed kernels.
    Produces AIR-ready traces.
    """

    DOMAIN_TAG = b"TK-ZK-WITNESS-v2"

    def __init__(self):
        self.step = 0
        self.trace: List[Dict[str, int]] = []
        self._prev_hash = hashlib.sha256(self.DOMAIN_TAG).digest()

    # --------------------------------------------------------

    def record(self, x1: int, x2: int, y: int):
        for name, v in [("x1", x1), ("x2", x2), ("y", y)]:
            if not (0 <= v <= 255):
                raise AIRViolation(
                    f"Range violation {name}={v} at step {self.step}"
                )

        row_bytes = (
            self.step.to_bytes(8, "little") +
            x1.to_bytes(1, "little") +
            x2.to_bytes(1, "little") +
            y.to_bytes(1, "little")
        )

        h = hashlib.sha256(self._prev_hash + row_bytes).digest()

        self.trace.append({
            "t": self.step,
            "x1": x1,
            "x2": x2,
            "y": y,
            "h": int.from_bytes(h, "big"),
        })

        self._prev_hash = h
        self.step += 1

    # --------------------------------------------------------

    def check_air(self):
        n = len(self.trace)

        for i in range(n):
            row = self.trace[i]

            # C1: time monotonicity
            if row["t"] != i:
                raise AIRViolation(
                    f"Time monotonicity violated at row {i}"
                )

            # C2: uint8 bounds
            for name in ("x1", "x2", "y"):
                v = row[name]
                if not (0 <= v <= 255):
                    raise AIRViolation(
                        f"Range violation {name}[{i}] = {v}"
                    )

            

            # C3: hash-chain consistency
            row_bytes = (
                row["t"].to_bytes(8, "little") +
                row["x1"].to_bytes(1, "little") +
                row["x2"].to_bytes(1, "little") +
                row["y"].to_bytes(1, "little")
            )

            prev = (
                self.trace[i-1]["h"].to_bytes(32, "big")
                if i > 0 else hashlib.sha256(self.DOMAIN_TAG).digest()
            )

            expected_hash = hashlib.sha256(prev + row_bytes).digest()

            if row["h"] != int.from_bytes(expected_hash, "big"):
                raise AIRViolation(
                    f"Hash consistency violated at row {i}"
                )

        return True

    # --------------------------------------------------------

    def export_trace_columns(self):
        self.check_air()
        return {
            "t": [r["t"] for r in self.trace],
            "x1": [r["x1"] for r in self.trace],
            "x2": [r["x2"] for r in self.trace],
            "y": [r["y"] for r in self.trace],
            "h": [r["h"] for r in self.trace],
        }

    # --------------------------------------------------------

    def final_commitment(self) -> bytes:
        self.check_air()
        return self._prev_hash

    # --------------------------------------------------------

    def reset(self):
        self.__init__()


# ============================================================
# Epoch Folding (IVC Accumulator)
# ============================================================

class TKEpochFolder:
    def __init__(self, modulus: int, alpha: int = 1315423911):
        self.p = modulus
        self.alpha = alpha
        self.acc = 0
        self.steps = 0

    def absorb(self, h: int):
        self.acc = (self.alpha * self.acc + h) % self.p
        self.steps += 1

    def root(self) -> int:
        return self.acc


# ============================================================
# Fault Injection
# ============================================================

class TKFaultInjector:
    def __init__(self, flip_mask: int = 0x01):
        self.flip_mask = flip_mask

    def inject(self, value: int) -> int:
        return value ^ self.flip_mask
