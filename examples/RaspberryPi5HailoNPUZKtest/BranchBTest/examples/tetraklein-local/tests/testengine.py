import tk_zk_witness_recorder as tk
recorder = tk.TKZKWitnessRecorder()

print(f"Implementation Engine : {type(recorder._impl)}")
print(f"Module Path           : {recorder._impl.__class__.__module__}")

# Verification of native binary linkage
try:
    from tk_zk_witness_recorder_cy import TKZKWitnessRecorderCy
    print("STATUS: Native Cython binary (libc.stdio) is LOADED.")
except ImportError:
    print("STATUS: Cython binary MISSING. Running in Python fallback mode.")
