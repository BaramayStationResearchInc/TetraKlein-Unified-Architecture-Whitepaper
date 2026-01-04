import torch
from tk_kernel import TetraKleinKernel

model = TetraKleinKernel(alpha=0.85)
model.eval()

x = torch.randn(1, 1)
u = torch.randn(1, 1)

torch.onnx.export(
    model,
    (x, u),
    "tk_kernel.onnx",
    input_names=["x", "u"],
    output_names=["y"],
    opset_version=11
)

print("Exported tk_kernel.onnx")
