from __future__ import annotations

import json
from typing import Any

from src.models.graph import Graph
from src.models.operators import FCOp, SpatialOp
from src.utils.exceptions import ParseError


SPATIAL_OPS = {"Conv", "Pool"}


def load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise ParseError(f"找不到输入文件: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ParseError(f"JSON 解析失败: {exc}") from exc


def parse_operator(op_dict: dict) -> SpatialOp | FCOp:
    op_type = op_dict.get("operator")
    if op_type in SPATIAL_OPS:
        return SpatialOp(
            operator=op_dict["operator"],
            in_W=op_dict["in_W"],
            in_H=op_dict["in_H"],
            in_channels=op_dict["in_channels"],
            out_W=op_dict["out_W"],
            out_H=op_dict["out_H"],
            out_channels=op_dict["out_channels"],
            kernel=op_dict["kernel"],
            stride=op_dict["stride"],
            padding=op_dict["padding"],
        )
    if op_type == "FC":
        return FCOp(
            operator=op_dict["operator"],
            isPrevFC=op_dict["isPrevFC"],
            in_features=op_dict["in_features"],
            out_features=op_dict["out_features"],
        )
    raise ParseError(f"不支持的算子类型: {op_type}")


def parse_graph(path: str) -> Graph:
    data = load_json(path)
    if not isinstance(data, list):
        raise ParseError("JSON 顶层必须是数组")
    if not data:
        raise ParseError("JSON 数组不能为空")

    operators = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ParseError(f"第 {index} 个算子不是对象")
        operators.append(parse_operator(item))
    return Graph(operators=operators)
