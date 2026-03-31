from __future__ import annotations

from src.validator.common_validator import (
    require_bool,
    require_kernel,
    require_keys,
    require_nonnegative_int,
    require_operator,
    require_positive_int,
)


SPATIAL_REQUIRED = [
    "operator",
    "in_W",
    "in_H",
    "in_channels",
    "out_W",
    "out_H",
    "out_channels",
    "kernel",
    "stride",
    "padding",
]

FC_REQUIRED = [
    "operator",
    "isPrevFC",
    "in_features",
    "out_features",
]


def validate_operator_dict(op_dict: dict, index: int) -> None:
    op_type = require_operator(op_dict, index)

    if op_type in {"Conv", "Pool"}:
        require_keys(op_dict, SPATIAL_REQUIRED, index)
        require_positive_int(op_dict["in_W"], "in_W", index)
        require_positive_int(op_dict["in_H"], "in_H", index)
        require_positive_int(op_dict["in_channels"], "in_channels", index)
        require_positive_int(op_dict["out_W"], "out_W", index)
        require_positive_int(op_dict["out_H"], "out_H", index)
        require_positive_int(op_dict["out_channels"], "out_channels", index)
        require_kernel(op_dict["kernel"], index)
        require_positive_int(op_dict["stride"], "stride", index)
        require_nonnegative_int(op_dict["padding"], "padding", index)
        return

    require_keys(op_dict, FC_REQUIRED, index)
    require_bool(op_dict["isPrevFC"], "isPrevFC", index)
    require_positive_int(op_dict["in_features"], "in_features", index)
    require_positive_int(op_dict["out_features"], "out_features", index)
