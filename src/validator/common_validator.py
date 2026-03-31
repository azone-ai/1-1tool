from __future__ import annotations

from typing import Any

from src.utils.exceptions import ValidationError


ALLOWED_OPERATORS = {"Conv", "Pool", "FC"}


def require_keys(op_dict: dict[str, Any], required_keys: list[str], index: int) -> None:
    for key in required_keys:
        if key not in op_dict:
            raise ValidationError(f"第 {index} 个算子缺少字段: {key}")


def require_positive_int(value: Any, field_name: str, index: int) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"第 {index} 个算子字段 {field_name} 必须是正整数")


def require_nonnegative_int(value: Any, field_name: str, index: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValidationError(f"第 {index} 个算子字段 {field_name} 必须是非负整数")


def require_bool(value: Any, field_name: str, index: int) -> None:
    if not isinstance(value, bool):
        raise ValidationError(f"第 {index} 个算子字段 {field_name} 必须是布尔值")


def require_kernel(kernel: Any, index: int) -> None:
    if not isinstance(kernel, list) or len(kernel) != 2:
        raise ValidationError(f"第 {index} 个算子字段 kernel 必须是长度为 2 的数组")
    if not all(isinstance(x, int) and x > 0 for x in kernel):
        raise ValidationError(f"第 {index} 个算子字段 kernel 中的值必须是正整数")


def require_operator(op_dict: dict[str, Any], index: int) -> str:
    op_type = op_dict.get("operator")
    if op_type is None:
        raise ValidationError(f"第 {index} 个算子缺少字段: operator")
    if op_type not in ALLOWED_OPERATORS:
        raise ValidationError(f"第 {index} 个算子类型不支持: {op_type}")
    return op_type
