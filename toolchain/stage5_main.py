from __future__ import annotations

import os
from pathlib import Path

from . import stage1_task_generator
from . import stage2_control_generator
from . import stage3_data_linker
from . import stage4_address_modifier
from . import stage6_dataflow_exporter


def run_pipeline(
    network_path: str | None = None,
    op_library_path: str | None = None,
    data_db_root: str | None = None,
    output_dir: str | None = None,
    split_output_dir: str | None = None,
) -> str:
    """
    运行工具链主流程，并自动导出拆分后的 PE dataflow 文件夹。
    """
    base_dir = Path(__file__).resolve().parent

    network_path_resolved = str(Path(network_path) if network_path else base_dir / "network_structure.json")
    op_library_path_resolved = str(Path(op_library_path) if op_library_path else base_dir / "Op_Library")
    data_db_root_resolved = str(Path(data_db_root) if data_db_root else base_dir / "Data_Library")
    output_dir_resolved = Path(output_dir) if output_dir else base_dir / "pipeline_output"
    split_output_dir_resolved = Path(split_output_dir) if split_output_dir else output_dir_resolved / "final_executable_config_split"

    original_task_file = os.path.join(output_dir_resolved, "1_original_tasks.txt")
    aligned_task_file = os.path.join(output_dir_resolved, "1_aligned_tasks.txt")
    control_task_file = os.path.join(output_dir_resolved, "2_control_and_tasks.txt")
    task_addresses_json = os.path.join(output_dir_resolved, "task_addresses.json")
    full_config_file = os.path.join(output_dir_resolved, "3_full_config_with_data.txt")
    data_addresses_json = os.path.join(output_dir_resolved, "data_addresses.json")
    final_output_file = os.path.join(output_dir_resolved, "final_executable_config.txt")

    os.makedirs(output_dir_resolved, exist_ok=True)

    try:
        stage1_task_generator.generate_task_instructions(
            network_path=network_path_resolved,
            library_path=op_library_path_resolved,
            original_output=original_task_file,
            aligned_output=aligned_task_file,
        )

        stage2_control_generator.generate_control_module(
            aligned_task_file=aligned_task_file,
            control_task_output_file=control_task_file,
            network_path=network_path_resolved,
            task_address_output_file=task_addresses_json,
        )

        stage3_data_linker.link_data_module(
            control_task_file=control_task_file,
            full_output_file=full_config_file,
            network_path=network_path_resolved,
            db_root=data_db_root_resolved,
            data_address_output_file=data_addresses_json,
        )

        stage4_address_modifier.modify_final_addresses(
            input_file=full_config_file,
            final_output_file=final_output_file,
            task_addresses_file=task_addresses_json,
            data_addresses_file=data_addresses_json,
        )

        stage6_dataflow_exporter.export_dataflow_folders(
            final_config_file=final_output_file,
            output_root=split_output_dir_resolved,
        )

        print(f"最终可执行激励文件位于: {final_output_file}")
        print(f"拆分后的 PE dataflow 位于: {split_output_dir_resolved}")
        return final_output_file

    except Exception as exc:
        raise RuntimeError(f"工具链运行失败: {exc}") from exc


if __name__ == "__main__":
    run_pipeline()
