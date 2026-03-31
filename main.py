from __future__ import annotations

import shutil
from pathlib import Path

from src.converter.txt_to_json import txt_to_json
from src.service.pipeline import build_and_generate_ir
from toolchain.stage5_main import run_pipeline


def main() -> None:
    base_dir = Path(__file__).resolve().parent

    input_json = base_dir / "data" / "input" / "model.json"
    ir_txt = base_dir / "data" / "intermediate" / "graph_ir.txt"
    output_json = base_dir / "data" / "output" / "graph.json"

    graph = build_and_generate_ir(str(input_json), str(ir_txt))
    txt_to_json(str(ir_txt), str(output_json))

    toolchain_network = base_dir / "toolchain" / "network_structure.json"
    shutil.copyfile(output_json, toolchain_network)

    final_file = run_pipeline(
        network_path=str(toolchain_network),
        op_library_path=str(base_dir / "toolchain" / "Op_Library"),
        data_db_root=str(base_dir / "toolchain" / "Data_Library"),
        output_dir=str(base_dir / "toolchain" / "pipeline_output"),
    )
    split_output_dir = base_dir / "toolchain" / "pipeline_output" / "final_executable_config_split"
    link_input_dir = base_dir / "toolchain" / "pipeline_output" / "link_input"

    print("Parsing and validation completed")
    print(f"Operator count: {len(graph.operators)}")
    print(f"Intermediate IR: {ir_txt.relative_to(base_dir)}")
    print(f"Converted JSON: {output_json.relative_to(base_dir)}")
    print(f"Toolchain input: {toolchain_network.relative_to(base_dir)}")
    print(f"Final executable config: {Path(final_file).relative_to(base_dir)}")
    print(f"Split PE dataflow: {split_output_dir.relative_to(base_dir)}")
    print(f"Link input bundle: {link_input_dir.relative_to(base_dir)}")


if __name__ == "__main__":
    main()
