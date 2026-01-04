from tk_hailo_executor import TKHailoKernelExecutor
from tk_zk_witness_recorder import TKZKWitnessRecorder


class TKEpochFolder:
    """
    Linear folding accumulator for recursive IVC.
    """

    def __init__(self, modulus: int, alpha: int = 1315423911):
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
    Hardware execution + ZK witness recording.
    Owns the full hardware lifecycle.
    """

    def __init__(self, hef_path: str, network_name: str):
        self.executor = TKHailoKernelExecutor(hef_path, network_name)
        self.witness = TKZKWitnessRecorder()
        self._closed = False

    # ------------------------------------------------------------
    # Normal execution (no divergence check)
    # ------------------------------------------------------------

    def step(self, x1: int, x2: int) -> int:
        if self._closed:
            raise RuntimeError("Executor is shut down")

        y = self.executor.run(
            input_layer1=x1,
            input_layer2=x2
        )
        self.witness.record(x1, x2, y)
        return y

    # ------------------------------------------------------------
    # Divergence-checked execution 
    # ------------------------------------------------------------

    def step_checked(self, x1: int, x2: int) -> int:
        """
        Execute kernel and enforce deterministic replay.
        """

        if self._closed:
            raise RuntimeError("Executor is shut down")

        y1 = self.executor.run(
            input_layer1=x1,
            input_layer2=x2
        )

        y2 = self.executor.run(
            input_layer1=x1,
            input_layer2=x2
        )

        if y1 != y2:
            raise RuntimeError(
                f"Divergence detected: y1={y1}, y2={y2}"
            )

        self.witness.record(x1, x2, y1)
        return y1

    # ------------------------------------------------------------

    def export_witness(self):
        return self.witness.export_trace_columns()

    def commitment(self) -> bytes:
        return self.witness.final_commitment()

    def shutdown(self):
        if not self._closed:
            self.executor.shutdown()
            self._closed = True

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass
