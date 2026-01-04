import torch
import torch.nn as nn

class TetraKleinKernel(nn.Module):
    def __init__(self, alpha=0.85):
        super().__init__()
        self.alpha = alpha

    def forward(self, x, u):
        return self.alpha * x + (1.0 - self.alpha) * u
