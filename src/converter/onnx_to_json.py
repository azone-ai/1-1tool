from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.io_utils import ensure_parent_dir

try:
    import onnx
    from onnx import shape_inference
except ImportError as exc:  # pragma: no cover - depends on environment
    raise ImportError(
        "ONNX support requires the 'onnx' package. Install it before using ONNX input."
    ) from exc


SPATIAL_CONV_OPS = {"Conv", "ConvInteger"}
SPATIAL_POOL_OPS = {"MaxPool", "AveragePool"}
FC_OPS = {"MatMul", "MatMulInteger", "Gemm"}


def _load_and_infer_onnx_model(path: str | Path) -> onnx.ModelProto:
    model = onnx.load(str(path))
    return shape_inference.infer_shapes(model)


def _attribute_map(node: onnx.NodeProto) -> dict[str, Any]:
    return {attribute.name: onnx.helper.get_attribute_value(attribute) for attribute in node.attribute}


def _build_shape_map(model: onnx.ModelProto) -> dict[str, list[int]]:
    shape_map: dict[str, list[int]] = {}

    def record_value_info(value_info: onnx.ValueInfoProto) -> None:
        tensor_type = value_info.type.tensor_type
        if not tensor_type.HasField("shape"):
            return

        dims: list[int] = []
        for dim in tensor_type.shape.dim:
            if dim.HasField("dim_value"):
                dims.append(dim.dim_value)
            else:
                raise ValueError(f"Dynamic tensor shape is not supported: {value_info.name}")
        shape_map[value_info.name] = dims

    for value in list(model.graph.value_info) + list(model.graph.input) + list(model.graph.output):
        record_value_info(value)

    for initializer in model.graph.initializer:
        shape_map.setdefault(initializer.name, list(initializer.dims))

    return shape_map


def _require_shape(shape_map: dict[str, list[int]], tensor_name: str) -> list[int]:
    if tensor_name not in shape_map:
        raise ValueError(f"Missing inferred shape for tensor: {tensor_name}")
    return shape_map[tensor_name]


def _require_symmetric_spatial_values(values: list[int], field_name: str, node_name: str) -> int:
    if not values:
        return 0
    if len(values) == 2:
        if values[0] != values[1]:
            raise ValueError(f"{field_name} must be symmetric for node {node_name}: {values}")
        return int(values[0])
    if len(values) == 4:
        top, left, bottom, right = values
        if top != bottom or left != right or top != left:
            raise ValueError(f"{field_name} must be symmetric for node {node_name}: {values}")
        return int(top)
    raise ValueError(f"Unsupported {field_name} format for node {node_name}: {values}")


def _require_equal_spatial_values(values: list[int], field_name: str, node_name: str) -> int:
    if len(values) != 2:
        raise ValueError(f"Expected 2D {field_name} for node {node_name}: {values}")
    if values[0] != values[1]:
        raise ValueError(f"{field_name} must use the same value on H/W in current JSON format for node {node_name}: {values}")
    return int(values[0])


def _extract_feature_count(shape: list[int], tensor_name: str) -> int:
    if not shape:
        raise ValueError(f"Empty tensor shape for {tensor_name}")
    if len(shape) == 1:
        return int(shape[0])
    feature_dims = shape[1:]
    feature_count = 1
    for dim in feature_dims:
        feature_count *= int(dim)
    return feature_count


def _convert_conv_node(node: onnx.NodeProto, shape_map: dict[str, list[int]]) -> dict[str, Any]:
    attributes = _attribute_map(node)
    node_name = node.name or node.output[0]

    if attributes.get("group", 1) != 1:
        raise ValueError(f"Grouped convolution is not supported in the current JSON format: {node_name}")

    dilations = list(attributes.get("dilations", [1, 1]))
    if dilations != [1, 1]:
        raise ValueError(f"Dilated convolution is not supported in the current JSON format: {node_name}")

    input_shape = _require_shape(shape_map, node.input[0])
    output_shape = _require_shape(shape_map, node.output[0])
    kernel_shape = list(attributes.get("kernel_shape", []))
    if not kernel_shape:
        weight_shape = _require_shape(shape_map, node.input[1])
        kernel_shape = [int(weight_shape[2]), int(weight_shape[3])]

    stride = _require_equal_spatial_values(list(attributes.get("strides", [1, 1])), "strides", node_name)
    padding = _require_symmetric_spatial_values(list(attributes.get("pads", [0, 0, 0, 0])), "pads", node_name)

    return {
        "operator": "Conv",
        "in_W": int(input_shape[3]),
        "in_H": int(input_shape[2]),
        "in_channels": int(input_shape[1]),
        "out_W": int(output_shape[3]),
        "out_H": int(output_shape[2]),
        "out_channels": int(output_shape[1]),
        "kernel": [int(kernel_shape[0]), int(kernel_shape[1])],
        "stride": stride,
        "padding": padding,
    }


def _convert_pool_node(node: onnx.NodeProto, shape_map: dict[str, list[int]]) -> dict[str, Any]:
    attributes = _attribute_map(node)
    node_name = node.name or node.output[0]

    if int(attributes.get("ceil_mode", 0)) != 0:
        raise ValueError(f"ceil_mode=1 pool is not supported in the current JSON format: {node_name}")

    input_shape = _require_shape(shape_map, node.input[0])
    output_shape = _require_shape(shape_map, node.output[0])
    kernel_shape = list(attributes.get("kernel_shape", []))
    if not kernel_shape:
        raise ValueError(f"Missing kernel_shape for pooling node: {node_name}")

    stride = _require_equal_spatial_values(list(attributes.get("strides", kernel_shape)), "strides", node_name)
    padding = _require_symmetric_spatial_values(list(attributes.get("pads", [0, 0, 0, 0])), "pads", node_name)

    return {
        "operator": "Pool",
        "in_W": int(input_shape[3]),
        "in_H": int(input_shape[2]),
        "in_channels": int(input_shape[1]),
        "out_W": int(output_shape[3]),
        "out_H": int(output_shape[2]),
        "out_channels": int(output_shape[1]),
        "kernel": [int(kernel_shape[0]), int(kernel_shape[1])],
        "stride": stride,
        "padding": padding,
    }


def _convert_fc_node(
    node: onnx.NodeProto,
    shape_map: dict[str, list[int]],
    previous_operator: dict[str, Any] | None,
) -> dict[str, Any]:
    input_shape = _require_shape(shape_map, node.input[0])
    output_shape = _require_shape(shape_map, node.output[0])

    return {
        "operator": "FC",
        "isPrevFC": bool(previous_operator and previous_operator["operator"] == "FC"),
        "in_features": _extract_feature_count(input_shape, node.input[0]),
        "out_features": _extract_feature_count(output_shape, node.output[0]),
    }


def convert_onnx_to_operator_list(onnx_path: str | Path) -> list[dict[str, Any]]:
    model = _load_and_infer_onnx_model(onnx_path)
    shape_map = _build_shape_map(model)

    operators: list[dict[str, Any]] = []
    for node in model.graph.node:
        if node.op_type in SPATIAL_CONV_OPS:
            operators.append(_convert_conv_node(node, shape_map))
            continue
        if node.op_type in SPATIAL_POOL_OPS:
            operators.append(_convert_pool_node(node, shape_map))
            continue
        if node.op_type in FC_OPS:
            operators.append(_convert_fc_node(node, shape_map, operators[-1] if operators else None))

    if not operators:
        raise ValueError(f"No supported Conv/Pool/FC operators were extracted from ONNX: {onnx_path}")

    return operators


def convert_onnx_to_json(onnx_path: str | Path, json_path: str | Path) -> list[dict[str, Any]]:
    operators = convert_onnx_to_operator_list(onnx_path)
    ensure_parent_dir(json_path)
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(operators, file, indent=2, ensure_ascii=False)
    return operators
