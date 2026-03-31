from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .operators import Operator


@dataclass
class Graph:
    operators: List[Operator]
