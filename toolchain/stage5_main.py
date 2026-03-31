from __future__ import annotations

import os
from pathlib import Path

from . import stage1_task_generator
from . import stage2_control_generator
from . import stage3_data_linker
from . import stage4_address_modifier


def run_pipeline(
    network_path: str | None = None,
    op_library_path: str | None = None,
    data_db_root: str | None = None,
    output_dir: str | None = None,
) -> str:
    """
    运行工具链主流程。

    参数默认相对于当前文件所在目录：
    - network_path: 网络结构 JSON
    - op_library_path: 算子库目录
    - data_db_root: 数据库目录
    - output_dir: 工具链输出目录

    返回：最终可执行激励文件路径。
    """
    base_dir = Path(__file__).resolve().parent

    NETWORK_PATH = str(Path(network_path) if network_path else base_dir / "network_structure.json")
    OP_LIBRARY_PATH = str(Path(op_library_path) if op_library_path else base_dir / "Op_Library")
    DATA_DB_ROOT = str(Path(data_db_root) if data_db_root else base_dir / "Data_Library")
    OUTPUT_DIR = str(Path(output_dir) if output_dir else base_dir / "pipeline_output")

    ORIGINAL_TASK_FILE = os.path.join(OUTPUT_DIR, "1_original_tasks.txt")
    ALIGNED_TASK_FILE = os.path.join(OUTPUT_DIR, "1_aligned_tasks.txt")
    CONTROL_TASK_FILE = os.path.join(OUTPUT_DIR, "2_control_and_tasks.txt")
    TASK_ADDRESSES_JSON = os.path.join(OUTPUT_DIR, "task_addresses.json")
    FULL_CONFIG_FILE = os.path.join(OUTPUT_DIR, "3_full_config_with_data.txt")
    DATA_ADDRESSES_JSON = os.path.join(OUTPUT_DIR, "data_addresses.json")
    FINAL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "final_executable_config.txt")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        stage1_task_generator.generate_task_instructions(
            network_path=NETWORK_PATH,
            library_path=OP_LIBRARY_PATH,
            original_output=ORIGINAL_TASK_FILE,
            aligned_output=ALIGNED_TASK_FILE,
        )

        stage2_control_generator.generate_control_module(
            aligned_task_file=ALIGNED_TASK_FILE,
            control_task_output_file=CONTROL_TASK_FILE,
            network_path=NETWORK_PATH,
            task_address_output_file=TASK_ADDRESSES_JSON,
        )

        stage3_data_linker.link_data_module(
            control_task_file=CONTROL_TASK_FILE,
            full_output_file=FULL_CONFIG_FILE,
            network_path=NETWORK_PATH,
            db_root=DATA_DB_ROOT,
            data_address_output_file=DATA_ADDRESSES_JSON,
        )

        stage4_address_modifier.modify_final_addresses(
            input_file=FULL_CONFIG_FILE,
            final_output_file=FINAL_OUTPUT_FILE,
            task_addresses_file=TASK_ADDRESSES_JSON,
            data_addresses_file=DATA_ADDRESSES_JSON,
        )

        print(f"最终可执行文件位于: {FINAL_OUTPUT_FILE}")
        return FINAL_OUTPUT_FILE

    except Exception as e:
        raise RuntimeError(f"工具链运行失败: {e}") from e


if __name__ == "__main__":
    run_pipeline()
