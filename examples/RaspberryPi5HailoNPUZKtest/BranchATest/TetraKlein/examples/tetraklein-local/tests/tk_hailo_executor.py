import numpy as np
from datetime import timedelta
from hailo_platform.pyhailort import _pyhailort as hailo


class TKHailoKernelExecutor:
    """
    Deterministic executor for a single Hailo HEF kernel.
    Intended for TetraKlein Layer-2 / Layer-5 execution.
    """

    def __init__(self, hef_path: str, network_name: str):
        self.hef_path = hef_path
        self.network_name = network_name
        self._closed = False

        # --- Device setup ---
        self._vdevice = hailo.VDevice.create(
            hailo.VDeviceParams.default()
        )

        # --- Infer model ---
        self._infer_model = self._vdevice.create_infer_model_from_file(
            hef_path, network_name
        )

        self._configured_model = self._infer_model.configure()
        self._configured_model.activate()

        # --- Bindings (persistent) ---
        self._bindings = self._configured_model.create_bindings()

        # --- Input / output names ---
        self.input_names = self._infer_model.get_input_names()
        self.output_names = self._infer_model.get_output_names()

        if len(self.output_names) != 1:
            raise ValueError("Executor assumes exactly one output stream")

        # --- Allocate buffers ---
        self._allocate_buffers()

    # ------------------------------------------------------------------

    def _allocate_buffers(self):
        self._input_buffers = {}

        for name in self.input_names:
            shape = self._infer_model.input(name).shape()
            buf = np.zeros(shape, dtype=np.uint8)
            self._input_buffers[name] = buf
            self._bindings.input(name).set_buffer(buf)

        out_name = self.output_names[0]
        out_shape = self._infer_model.output(out_name).shape()
        self._output_buffer = np.zeros(out_shape, dtype=np.uint8)
        self._bindings.output(out_name).set_buffer(self._output_buffer)

    # ------------------------------------------------------------------

    def run(self, **inputs) -> int:
        if self._closed:
            raise RuntimeError("Executor has been shut down")

        for name in self.input_names:
            key = name.split("/")[-1]
            if key not in inputs:
                raise KeyError(f"Missing input: {key}")
            self._input_buffers[name].fill(inputs[key])

        self._configured_model.run(
            self._bindings,
            timedelta(milliseconds=100)
        )

        return int(self._output_buffer.flatten()[0])

    # ------------------------------------------------------------------

    def shutdown(self):
        if self._closed:
            return

        self._closed = True

        # IMPORTANT: drop bindings first
        self._bindings = None
        self._input_buffers = None
        self._output_buffer = None

        try:
            self._configured_model.deactivate()
        except Exception:
            pass

        # Explicitly drop model objects before releasing device
        self._configured_model = None
        self._infer_model = None

        try:
            self._vdevice.release()
        except Exception:
            pass

        self._vdevice = None

    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.shutdown()

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass
