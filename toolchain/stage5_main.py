from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import stage1_task_generator
from . import stage2_control_generator
from . import stage3_data_linker
from . import stage4_address_modifier
from . import stage6_dataflow_exporter
from . import stage7_link_input_packager


def _resolve_output_paths(
    base_dir: Path,
    output_dir: str | None,
    split_output_dir: str | None,
    link_input_dir: str | None,
) -> tuple[Path, Path, Path, Path]:
    output_dir_resolved = Path(output_dir) if output_dir else base_dir / "pipeline_output"
    split_output_dir_resolved = Path(split_output_dir) if split_output_dir else output_dir_resolved / "final_executable_config_split"
    link_input_dir_resolved = Path(link_input_dir) if link_input_dir else output_dir_resolved / "link_input"
    final_output_file = output_dir_resolved / "final_executable_config.txt"
    return output_dir_resolved, split_output_dir_resolved, link_input_dir_resolved, final_output_file


def _postprocess_final_config(
    final_output_file: str | Path,
    split_output_dir: str | Path,
    link_input_dir: str | Path,
) -> str:
    stage6_dataflow_exporter.export_dataflow_folders(
        final_config_file=final_output_file,
        output_root=split_output_dir,
    )

    stage7_link_input_packager.prepare_link_input_bundle(
        final_config_file=final_output_file,
        split_output_dir=split_output_dir,
        bundle_dir=link_input_dir,
    )

    print(f"Final executable config written to: {final_output_file}")
    print(f"Split PE dataflow written to: {split_output_dir}")
    print(f"Link input bundle written to: {link_input_dir}")
    return str(final_output_file)


def process_existing_final_config(
    final_config_file: str | Path,
    output_dir: str | None = None,
    split_output_dir: str | None = None,
    link_input_dir: str | None = None,
) -> str:
    """
    Reuse the existing split/link post-processing stages on a provided final executable config.
    """
    base_dir = Path(__file__).resolve().parent
    source_final_config = Path(final_config_file).expanduser().resolve()
    if not source_final_config.exists():
        raise FileNotFoundError(f"Final executable config not found: {source_final_config}")

    output_dir_resolved, split_output_dir_resolved, link_input_dir_resolved, final_output_path = _resolve_output_paths(
        base_dir=base_dir,
        output_dir=output_dir,
        split_output_dir=split_output_dir,
        link_input_dir=link_input_dir,
    )
    output_dir_resolved.mkdir(parents=True, exist_ok=True)

    if source_final_config != final_output_path.resolve():
        shutil.copy2(source_final_config, final_output_path)

    return _postprocess_final_config(
        final_output_file=final_output_path,
        split_output_dir=split_output_dir_resolved,
        link_input_dir=link_input_dir_resolved,
    )


def run_pipeline(
    network_path: str | None = None,
    op_library_path: str | None = None,
    data_db_root: str | None = None,
    output_dir: str | None = None,
    split_output_dir: str | None = None,
    link_input_dir: str | None = None,
) -> str:
    """
    Run the toolchain pipeline, split PE dataflow, and package link inputs.
    """
    base_dir = Path(__file__).resolve().parent

    network_path_resolved = str(Path(network_path) if network_path else base_dir / "network_structure.json")
    op_library_path_resolved = str(Path(op_library_path) if op_library_path else base_dir / "Op_Library")
    data_db_root_resolved = str(Path(data_db_root) if data_db_root else base_dir / "Data_Library")
    output_dir_resolved, split_output_dir_resolved, link_input_dir_resolved, final_output_path = _resolve_output_paths(
        base_dir=base_dir,
        output_dir=output_dir,
        split_output_dir=split_output_dir,
        link_input_dir=link_input_dir,
    )

    original_task_file = os.path.join(output_dir_resolved, "1_original_tasks.txt")
    aligned_task_file = os.path.join(output_dir_resolved, "1_aligned_tasks.txt")
    control_task_file = os.path.join(output_dir_resolved, "2_control_and_tasks.txt")
    task_addresses_json = os.path.join(output_dir_resolved, "task_addresses.json")
    full_config_file = os.path.join(output_dir_resolved, "3_full_config_with_data.txt")
    data_addresses_json = os.path.join(output_dir_resolved, "data_addresses.json")

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
            final_output_file=str(final_output_path),
            task_addresses_file=task_addresses_json,
            data_addresses_file=data_addresses_json,
        )

        return _postprocess_final_config(
            final_output_file=final_output_path,
            split_output_dir=split_output_dir_resolved,
            link_input_dir=link_input_dir_resolved,
        )

    except Exception as exc:
        raise RuntimeError(f"Toolchain pipeline failed: {exc}") from exc


if __name__ == "__main__":
    run_pipeline()
