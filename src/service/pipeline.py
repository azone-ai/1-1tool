from __future__ import annotations

import json

from src.generator.txt_generator import generate_txt
from src.parser.json_parser import load_json, parse_graph
from src.validator.operator_validator import validate_operator_dict
from src.validator.graph_validator import validate_graph


def validate_raw_json(path: str) -> None:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("JSON 顶层必须是数组")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 个算子不是对象")
        validate_operator_dict(item, index)


def build_and_generate_ir(input_json_path: str, output_txt_path: str):
    validate_raw_json(input_json_path)
    graph = parse_graph(input_json_path)
    validate_graph(graph)
    generate_txt(graph, output_txt_path)
    return graph


def load_raw_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
