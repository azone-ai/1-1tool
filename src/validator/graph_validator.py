from __future__ import annotations

from src.models.graph import Graph
from src.models.operators import FCOp, SpatialOp
from src.utils.exceptions import ValidationError


def calc_spatial_output(in_size: int, kernel: int, stride: int, padding: int) -> int:
    numerator = in_size - kernel + 2 * padding
    if numerator < 0:
        raise ValidationError("卷积/池化参数非法，导致输出尺寸为负")
    if numerator % stride != 0:
        raise ValidationError("卷积/池化参数非法，输出尺寸不是整数")
    return numerator // stride + 1


def validate_spatial_formula(op: SpatialOp, index: int) -> None:
    expected_out_w = calc_spatial_output(op.in_W, op.kernel[0], op.stride, op.padding)
    expected_out_h = calc_spatial_output(op.in_H, op.kernel[1], op.stride, op.padding)

    if expected_out_w != op.out_W:
        raise ValidationError(
            f"第 {index} 个算子 out_W 不匹配，期望 {expected_out_w}，实际 {op.out_W}"
        )
    if expected_out_h != op.out_H:
        raise ValidationError(
            f"第 {index} 个算子 out_H 不匹配，期望 {expected_out_h}，实际 {op.out_H}"
        )

    if op.operator == "Pool" and op.out_channels != op.in_channels:
        raise ValidationError(
            f"第 {index} 个 Pool 算子通道数不应变化，in_channels={op.in_channels}, out_channels={op.out_channels}"
        )


def validate_connection(prev_op, next_op, prev_index: int, next_index: int) -> None:
    if isinstance(prev_op, SpatialOp) and isinstance(next_op, SpatialOp):
        if prev_op.out_W != next_op.in_W:
            raise ValidationError(f"第 {prev_index} 层与第 {next_index} 层宽度不匹配")
        if prev_op.out_H != next_op.in_H:
            raise ValidationError(f"第 {prev_index} 层与第 {next_index} 层高度不匹配")
        if prev_op.out_channels != next_op.in_channels:
            raise ValidationError(f"第 {prev_index} 层与第 {next_index} 层通道数不匹配")
        return

    if isinstance(prev_op, SpatialOp) and isinstance(next_op, FCOp):
        expected_features = prev_op.out_W * prev_op.out_H * prev_op.out_channels
        if next_op.isPrevFC:
            raise ValidationError(f"第 {next_index} 层前一层不是 FC，isPrevFC 应为 false")
        if expected_features != next_op.in_features:
            raise ValidationError(
                f"第 {next_index} 层 FC 输入特征数不匹配，期望 {expected_features}，实际 {next_op.in_features}"
            )
        return

    if isinstance(prev_op, FCOp) and isinstance(next_op, FCOp):
        if not next_op.isPrevFC:
            raise ValidationError(f"第 {next_index} 层前一层是 FC，isPrevFC 应为 true")
        if prev_op.out_features != next_op.in_features:
            raise ValidationError(
                f"第 {prev_index} 层与第 {next_index} 层 FC 特征数不匹配"
            )
        return

    if isinstance(prev_op, FCOp) and isinstance(next_op, SpatialOp):
        raise ValidationError(f"第 {prev_index} 层为 FC，不支持再连接到空间算子 {next_index}")


def validate_graph(graph: Graph) -> None:
    if not graph.operators:
        raise ValidationError("图中没有算子")

    for index, op in enumerate(graph.operators):
        if isinstance(op, SpatialOp):
            validate_spatial_formula(op, index)

    for i in range(len(graph.operators) - 1):
        validate_connection(graph.operators[i], graph.operators[i + 1], i, i + 1)
