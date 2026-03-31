from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


TASK_INDEX_START_LINE = 513
BINARY_LINE_WIDTH = 128
PE_CONFIG_PAYLOAD_WIDTH = 108
HALF_LINE_WIDTH = 64
PE_PREFIX = "001"
FILLER_LINE = "1" * BINARY_LINE_WIDTH

# According to the PE bit-field definition, pool_size is stored in bits 18:15
# of the 108-bit PE payload. Pool tasks should expose an actual pooling window
# size there, while the non-pooling tasks in the current executable format do not.
POOL_SIZE_HIGH_BIT = 18
POOL_SIZE_LOW_BIT = 15
POOL_SIZE_MIN = 2
POOL_SIZE_MAX = 7


@dataclass(frozen=True)
class TaskDescriptor:
    task_id: int
    actual_line: int
    line_count: int


def _normalize_binary_lines(file_path: str | Path) -> list[str]:
    return [line.strip() for line in Path(file_path).read_text(encoding="utf-8").splitlines()]


def parse_task_descriptors(
    final_config_file: str | Path,
    task_index_start_line: int = TASK_INDEX_START_LINE,
) -> list[TaskDescriptor]:
    lines = _normalize_binary_lines(final_config_file)
    descriptors: list[TaskDescriptor] = []

    for line in lines[task_index_start_line - 1 :]:
        if len(line) != BINARY_LINE_WIDTH or set(line) - {"0", "1"}:
            break
        if line == FILLER_LINE:
            break

        start_addr = int(line[-64:-32], 2)
        line_count = int(line[-32:], 2)
        if line_count <= 0:
            continue

        descriptors.append(
            TaskDescriptor(
                task_id=len(descriptors) + 1,
                actual_line=start_addr // 16 + 1,
                line_count=line_count,
            )
        )

    return descriptors


def _extract_task_pe_lines(lines: list[str], descriptor: TaskDescriptor) -> list[str]:
    start_idx = descriptor.actual_line - 1
    end_idx = min(start_idx + descriptor.line_count, len(lines))

    pe_lines: list[str] = []
    for line in lines[start_idx:end_idx]:
        if not line.startswith(PE_PREFIX):
            break
        pe_lines.append(line)

    if pe_lines:
        pe_lines = pe_lines[:-1]

    if len(pe_lines) % 2 != 0:
        raise ValueError(
            f"Task {descriptor.task_id} has an odd number of PE config lines after removing the startup line: {len(pe_lines)}"
        )

    return pe_lines


def _extract_pe_field_value(line: str, high_bit: int, low_bit: int) -> int:
    if len(line) != BINARY_LINE_WIDTH:
        raise ValueError(f"Expected a 128-bit PE line, got {len(line)} bits")
    if not (0 <= low_bit <= high_bit < PE_CONFIG_PAYLOAD_WIDTH):
        raise ValueError(f"Invalid PE field range: {high_bit}:{low_bit}")

    payload = line[-PE_CONFIG_PAYLOAD_WIDTH:]
    start_idx = PE_CONFIG_PAYLOAD_WIDTH - 1 - high_bit
    end_idx = PE_CONFIG_PAYLOAD_WIDTH - low_bit
    return int(payload[start_idx:end_idx], 2)


def _task_is_pooling(pe_lines: list[str]) -> bool:
    for line in pe_lines:
        pool_size = _extract_pe_field_value(line, POOL_SIZE_HIGH_BIT, POOL_SIZE_LOW_BIT)
        if POOL_SIZE_MIN <= pool_size <= POOL_SIZE_MAX:
            return True
    return False


def _split_pe_pair_to_four_lines(first_line: str, second_line: str) -> list[str]:
    return [
        first_line[:HALF_LINE_WIDTH],
        first_line[HALF_LINE_WIDTH:],
        second_line[:HALF_LINE_WIDTH],
        second_line[HALF_LINE_WIDTH:],
    ]


def export_dataflow_folders(
    final_config_file: str | Path,
    output_root: str | Path,
    task_index_start_line: int = TASK_INDEX_START_LINE,
) -> Path:
    final_path = Path(final_config_file)
    output_path = Path(output_root)
    lines = _normalize_binary_lines(final_path)
    descriptors = parse_task_descriptors(final_path, task_index_start_line=task_index_start_line)

    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    total_pe_files = 0
    exported_task_mappings: list[tuple[int, int]] = []
    skipped_pooling_task_ids: list[int] = []

    for descriptor in descriptors:
        pe_lines = _extract_task_pe_lines(lines, descriptor)
        if _task_is_pooling(pe_lines):
            skipped_pooling_task_ids.append(descriptor.task_id)
            continue

        exported_task_id = len(exported_task_mappings) + 1
        task_dir = output_path / str(exported_task_id)
        dataflow_dir = task_dir / "dataflow"
        insflow_dir = task_dir / "insflow"
        dataflow_dir.mkdir(parents=True, exist_ok=True)
        insflow_dir.mkdir(parents=True, exist_ok=True)

        for pe_index in range(0, len(pe_lines), 2):
            file_path = dataflow_dir / f"PE{pe_index // 2:02d}.txt"
            output_lines = _split_pe_pair_to_four_lines(pe_lines[pe_index], pe_lines[pe_index + 1])
            file_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
            total_pe_files += 1

        exported_task_mappings.append((exported_task_id, descriptor.task_id))

    print(f"Dataflow split completed: {output_path}")
    print(f"Exported {len(exported_task_mappings)} tasks and {total_pe_files} PE files")
    if exported_task_mappings:
        mapping_text = ", ".join(
            f"{exported_task_id}->{original_task_id}"
            for exported_task_id, original_task_id in exported_task_mappings
        )
        print(f"Export task mapping: {mapping_text}")
    if skipped_pooling_task_ids:
        skipped_list = ", ".join(str(task_id) for task_id in skipped_pooling_task_ids)
        print(f"Skipped pooling tasks: {skipped_list}")
    return output_path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split final_executable_config.txt into task dataflow folders")
    parser.add_argument("final_config_file", help="Path to final_executable_config.txt")
    parser.add_argument("output_root", help="Output directory for the split task folders")
    parser.add_argument(
        "--task-index-start-line",
        type=int,
        default=TASK_INDEX_START_LINE,
        help="1-based start line of the task index table, default is 513",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    export_dataflow_folders(
        final_config_file=args.final_config_file,
        output_root=args.output_root,
        task_index_start_line=args.task_index_start_line,
    )


if __name__ == "__main__":
    main()
