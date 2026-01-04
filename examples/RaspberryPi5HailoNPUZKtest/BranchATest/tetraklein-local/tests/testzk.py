from tk_hailo_zk_executor import TKHailoZKExecutor

# Create executor
zk_exec = TKHailoZKExecutor(
    "/home/baramaystation1/tkhailo/hef/tk_kernel.hef",
    "tk_kernel"
)

# Run a few steps
for x1, x2 in [(5, 3), (10, 2), (7, 7), (1, 1)]:
    y = zk_exec.step(x1, x2)
    print(f"{x1}, {x2} -> {y}")

# Export witness
trace = zk_exec.export_witness()
root = zk_exec.commitment()

print("Witness columns:")
for k, v in trace.items():
    print(k, v)

print("Final commitment:", root.hex())

zk_exec.shutdown()
