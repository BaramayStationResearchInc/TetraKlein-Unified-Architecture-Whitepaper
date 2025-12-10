# 🧠 TetraKlein GPU Reality Test Archive
**Date:** 2025-12-03 19:04:39  
**GPU:** Tesla T4  
**CUDA:** Cuda compilation tools, release 12.5, V12.5.82  
**Python:** Python 3.12.12  
**Coq:** The Coq Proof Assistant, version 8.15.0  

---

### Contents
| File | Description |
|------|--------------|
| `tetraklein_reality.v` | Coq formal proof source |
| `*.vo` | Compiled Coq proof objects |
| `tetraklein_logs/full_output.txt` | Console log of verification run |
| `tetraklein_logs/tetraklein_gpu_plot.png` | GPU evolution plot |
| `tetraklein_logs/symbolic_check.txt` | Symbolic validation outputs |
| `tetraklein_logs/gpu_values.npy`, `gpu_norms.npy` | Sample numerical traces |
| `tetraklein_logs/run_metadata.json` | Runtime and environment metadata |
| `tetraklein_logs/README.md` | This summary |

---

### Citation
> TetraKlein GPU Reality Test (CUDA 12.4, Coq 8.15).  
> Reproducible archive generated automatically via hybrid symbolic + GPU validation.

---

### Notes
This bundle contains both the *formal* logical proof and the *numerical* CUDA execution traces, allowing full reproducibility on any compatible environment.
