from __future__ import annotations

from src.models.graph import Graph
from src.models.operators import FCOp, SpatialOp
from src.utils.io_utils import ensure_parent_dir


def graph_to_ir_lines(graph: Graph) -> list[str]:
    lines: list[str] = []
    for op in graph.operators:
        if isinstance(op, SpatialOp):
            line = (
                f"{op.operator} "
                f"in_W={op.in_W} "
                f"in_H={op.in_H} "
                f"in_channels={op.in_channels} "
                f"out_W={op.out_W} "
                f"out_H={op.out_H} "
                f"out_channels={op.out_channels} "
                f"kernel={op.kernel[0]},{op.kernel[1]} "
                f"stride={op.stride} "
                f"padding={op.padding}"
            )
        elif isinstance(op, FCOp):
            line = (
                f"{op.operator} "
                f"isPrevFC={'true' if op.isPrevFC else 'false'} "
                f"in_features={op.in_features} "
                f"out_features={op.out_features}"
            )
        else:
            raise TypeError(f"未知算子对象类型: {type(op)!r}")
        lines.append(line)
    return lines


def generate_txt(graph: Graph, output_path: str) -> None:
    ensure_parent_dir(output_path)
    lines = graph_to_ir_lines(graph)
    with open(output_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
