from __future__ import annotations

import json

from src.utils.io_utils import ensure_parent_dir


def parse_value(value: str):
    if value == "true":
        return True
    if value == "false":
        return False
    if "," in value:
        parts = value.split(",")
        if all(part.strip().isdigit() for part in parts):
            return [int(part) for part in parts]
    if value.isdigit():
        return int(value)
    return value


def txt_to_json(txt_path: str, json_path: str) -> list[dict]:
    result: list[dict] = []

    with open(txt_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if not parts:
                continue

            op = {"operator": parts[0]}
            for item in parts[1:]:
                if "=" not in item:
                    raise ValueError(f"第 {line_no} 行格式错误，缺少 '=': {item}")
                key, value = item.split("=", 1)
                op[key] = parse_value(value)
            result.append(op)

    ensure_parent_dir(json_path)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result
