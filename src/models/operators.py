from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union


@dataclass
class SpatialOp:
    operator: str
    in_W: int
    in_H: int
    in_channels: int
    out_W: int
    out_H: int
    out_channels: int
    kernel: List[int]
    stride: int
    padding: int


@dataclass
class FCOp:
    operator: str
    isPrevFC: bool
    in_features: int
    out_features: int


Operator = Union[SpatialOp, FCOp]
