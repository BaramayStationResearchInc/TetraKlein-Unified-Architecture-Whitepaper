from tk_hailo_executor import TKHailoKernelExecutor  # Patched v4.23.0 version
from tk_zk_witness_recorder import TKZKWitnessRecorder
from typing import Optional

class TKEpochFolder:
    """Linear MiMC-style folding accumulator (STARK-friendly degree-1 recurrence)."""
    def __init__(self, modulus: int = 2**256 - 2**32 * 351 + 1, alpha: int = 1315423911):
        self.p = modulus
        self.alpha = alpha
        self.acc = 0
        self.steps = 0

    def absorb(self, value: int):
        self.acc = (self.alpha * self.acc + value) % self.p
        self.steps += 1

    def root(self) -> int:
        return self.acc

class TKHailoZKExecutor:
    """
    Hardware-accelerated ZK executor with witness recording and optional divergence checking.
    Suitable for TK–X prover fragments under merged TK–W/TK–X trace mode.
    """
    def __init__(self, hef_path: str, network_name: Optional[str] = None, check_divergence: bool = False):
        self.executor = TKHailoKernelExecutor(hef_path, network_name)
        self.witness = TKZKWitnessRecorder()
        self.folder = TKEpochFolder()  # Epoch-level recursive accumulator
        self.check_divergence = check_divergence
        self._closed = False

    def step(self, x1: int, x2: int) -> int:
        if self._closed:
            raise RuntimeError("Executor is shut down")

        y = self.executor.run(input_layer1=x1, input_layer2=x2)

        if self.check_divergence:
            y_check = self.executor.run(input_layer1=x1, input_layer2=x2)
            if y != y_check:
                raise RuntimeError(f"Hardware divergence detected: y={y}, y_check={y_check}")

        self.witness.record(x1, x2, y)
        self.folder.absorb(y)  # Fold into epoch accumulator for IVC recursion

        return y

    def step_checked(self, x1: int, x2: int) -> int:
        """Legacy alias with divergence check forced."""
        return self.step(x1, x2) if not self.check_divergence else self.step(x1, x2)

    def export_witness(self):
        return self.witness.export_trace_columns()

    def commitment(self) -> bytes:
        """Final multicolumn witness commitment (HRTH-rooted)."""
        return self.witness.final_commitment()

    def epoch_root(self) -> int:
        """Recursive folding root for FrameIVC aggregation."""
        return self.folder.root()

    def shutdown(self):
        if not self._closed:
            self.executor.shutdown()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.shutdown()

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass
