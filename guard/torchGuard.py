# -*- coding: utf-8 -*-

"""
"""

import torch
from .guard import Guard


class TorchGuard(Guard):
    def serialize(self, path, **kwargs):
        data = {k: k.state_dict() for k in kwargs}
        torch.save(data, path + ".pth.tar")

    def deserialize(self, path, **kwargs):
        data = torch.load(path + ".pth.tar")
        for k in kwargs:
            kwargs[k].load_state_dict(data[k])
