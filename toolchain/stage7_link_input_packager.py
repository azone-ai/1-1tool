from __future__ import annotations

import shutil
from pathlib import Path

from . import stage6_dataflow_exporter


BINARY_LINE_WIDTH = 128
FIFO_START_LINE = stage6_dataflow_exporter.TASK_INDEX_START_LINE
CONTROL_BLOCK_LINE_COUNT = 1536
FIFO_COUNT_BIT_START = 80
FIFO_COUNT_BIT_END = 96
FILLER_LINE = "1" * BINARY_LINE_WIDTH


def _replace_fifo_count(first_line: str, fifo_count: int) -> str:
    fifo_count_binary = format(fifo_count, "016b")
    return first_line[:FIFO_COUNT_BIT_START] + fifo_count_binary + first_line[FIFO_COUNT_BIT_END:]


def _filter_pooling_fifo_entries(link_final_config_file: Path) -> list[int]:
    lines = link_final_config_file.read_text(encoding="utf-8").splitlines()
    pooling_task_ids = stage6_dataflow_exporter.find_pooling_task_ids(link_final_config_file)

    if not pooling_task_ids:
        return []

    fifo_region_start_idx = FIFO_START_LINE - 1
    fifo_region_end_idx = CONTROL_BLOCK_LINE_COUNT
    fifo_entries = lines[fifo_region_start_idx:fifo_region_end_idx]
    keep_mask = [(task_id not in pooling_task_ids) for task_id in range(1, len(fifo_entries) + 1)]

    kept_fifo_entries = [
        fifo_entry
        for fifo_entry, keep_entry in zip(fifo_entries, keep_mask)
        if keep_entry and fifo_entry != FILLER_LINE
    ]

    rebuilt_fifo_region = kept_fifo_entries + [FILLER_LINE] * (len(fifo_entries) - len(kept_fifo_entries))
    lines[fifo_region_start_idx:fifo_region_end_idx] = rebuilt_fifo_region
    lines[0] = _replace_fifo_count(lines[0], len(kept_fifo_entries))

    link_final_config_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pooling_task_ids


def prepare_link_input_bundle(
    final_config_file: str | Path,
    split_output_dir: str | Path,
    bundle_dir: str | Path,
) -> Path:
    final_config_path = Path(final_config_file)
    split_output_path = Path(split_output_dir)
    bundle_path = Path(bundle_dir)

    if not final_config_path.exists():
        raise FileNotFoundError(f"Final executable config not found: {final_config_path}")
    if not split_output_path.exists():
        raise FileNotFoundError(f"Split dataflow folder not found: {split_output_path}")

    if bundle_path.exists():
        shutil.rmtree(bundle_path)
    bundle_path.mkdir(parents=True, exist_ok=True)

    bundled_final_config_path = bundle_path / final_config_path.name
    shutil.copy2(final_config_path, bundled_final_config_path)
    shutil.copytree(split_output_path, bundle_path / split_output_path.name)
    skipped_pooling_task_ids = _filter_pooling_fifo_entries(bundled_final_config_path)

    print(f"Link input bundle created: {bundle_path}")
    if skipped_pooling_task_ids:
        skipped_list = ", ".join(str(task_id) for task_id in skipped_pooling_task_ids)
        print(f"Filtered pooling FIFO entries from link input final config: {skipped_list}")
    return bundle_path
