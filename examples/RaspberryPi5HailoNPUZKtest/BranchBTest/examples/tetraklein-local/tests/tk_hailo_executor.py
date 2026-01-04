import numpy as np
from datetime import timedelta
from hailo_platform.pyhailort import _pyhailort as hailo


class TKHailoKernelExecutor:
    """
    Deterministic executor for a single Hailo HEF kernel.
    Uses low-level _pyhailort API for TetraKlein Layer-2 / Layer-5 verifiable offload.
    """
    
    def __init__(self, hef_path: str, network_name: str = "tk_kernel"):
        self.hef_path = hef_path
        self.network_name = network_name
        self._closed = False

        # Load HEF
        self._hef = hailo.Hef.create_from_file(hef_path)

        # Create VDevice
        vdevice_params = hailo.VDeviceParams.default()
        self._vdevice = hailo.VDevice.create(vdevice_params)

        # Create InferModel
        self._infer_model = self._vdevice.create_infer_model_from_file(
            hef_path, network_name
        )
        
        # Configure and activate
        self._configured_model = self._infer_model.configure()
        self._configured_model.activate()

        # Cache input/output metadata
        self._input_names = self._infer_model.get_input_names()
        self._output_names = self._infer_model.get_output_names()

        self._input_shapes = {}
        for name in self._input_names:
            self._input_shapes[name] = self._infer_model.input(name).shape()

        self._output_shapes = {}
        for name in self._output_names:
            self._output_shapes[name] = self._infer_model.output(name).shape()

    @property
    def input_names(self):
        return self._input_names

    @property
    def output_names(self):
        return self._output_names

    @property
    def input_shapes(self):
        return self._input_shapes

    @property
    def output_shapes(self):
        return self._output_shapes

    def run(self, **inputs) -> int:
        """
        Run inference with named inputs.
        Returns scalar output (first element of first output tensor).
        """
        if self._closed:
            raise RuntimeError("Executor has been shut down")

        bindings = self._configured_model.create_bindings()

        # Set inputs
        for name in self._input_names:
            short_name = name.split("/")[-1]
            if short_name in inputs:
                data = inputs[short_name]
            elif name in inputs:
                data = inputs[name]
            else:
                raise KeyError(f"Missing input: {name} (or {short_name})")
            
            expected_shape = self._input_shapes[name]
            data = np.array(data, dtype=np.uint8).reshape(expected_shape)
            bindings.input(name).set_buffer(data)

        # Prepare output buffer
        out_name = self._output_names[0]
        out_shape = self._output_shapes[out_name]
        output_buffer = np.zeros(out_shape, dtype=np.uint8)
        bindings.output(out_name).set_buffer(output_buffer)

        # Run inference
        self._configured_model.run(bindings, timedelta(seconds=10))

        return int(output_buffer.flatten()[0])

    def run_full(self, **inputs) -> dict:
        """
        Run inference with named inputs.
        Returns dict of output name -> numpy array.
        """
        if self._closed:
            raise RuntimeError("Executor has been shut down")

        bindings = self._configured_model.create_bindings()

        # Set inputs
        for name in self._input_names:
            short_name = name.split("/")[-1]
            if short_name in inputs:
                data = inputs[short_name]
            elif name in inputs:
                data = inputs[name]
            else:
                raise KeyError(f"Missing input: {name} (or {short_name})")
            
            expected_shape = self._input_shapes[name]
            data = np.array(data, dtype=np.uint8).reshape(expected_shape)
            bindings.input(name).set_buffer(data)

        # Prepare output buffers
        output_buffers = {}
        for name in self._output_names:
            shape = self._output_shapes[name]
            buf = np.zeros(shape, dtype=np.uint8)
            bindings.output(name).set_buffer(buf)
            output_buffers[name] = buf

        # Run inference
        self._configured_model.run(bindings, timedelta(seconds=10))

        return output_buffers

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self._configured_model = None
        self._infer_model = None
        self._vdevice = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.shutdown()

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass
