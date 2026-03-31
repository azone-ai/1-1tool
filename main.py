from __future__ import annotations

import argparse
import contextlib
import io
import shutil
from pathlib import Path

from src.converter.txt_to_json import txt_to_json
from src.service.pipeline import build_and_generate_ir
from toolchain.stage5_main import process_existing_final_config, run_pipeline


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the graph IR/toolchain pipeline or postprocess an existing final executable config")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input-model",
        help="Path to the input model file. Supports .json and .onnx. "
        "If omitted, data/input/model.onnx is preferred when it exists, otherwise data/input/model.json is used.",
    )
    input_group.add_argument(
        "--input-final-config",
        help="Path to an existing final_executable_config.txt. "
        "When provided, the upstream graph conversion and toolchain generation stages are skipped, "
        "and only the split/link-input postprocessing stages are run.",
    )
    parser.add_argument(
        "--converted-json-output",
        help="Optional output path for the JSON converted from ONNX. Only used when the input model is .onnx.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed stage logs and intermediate output information.",
    )
    return parser


def _resolve_input_model_path(base_dir: Path, input_model: str | None) -> Path:
    if input_model:
        return Path(input_model).expanduser().resolve()

    default_onnx = base_dir / "data" / "input" / "model.onnx"
    if default_onnx.exists():
        return default_onnx

    return base_dir / "data" / "input" / "model.json"


def _prepare_input_json(
    base_dir: Path,
    input_model: str | None,
    converted_json_output: str | None,
) -> tuple[Path, str, Path | None]:
    input_model_path = _resolve_input_model_path(base_dir, input_model)
    if not input_model_path.exists():
        raise FileNotFoundError(f"Input model file not found: {input_model_path}")

    suffix = input_model_path.suffix.lower()
    if suffix == ".json":
        return input_model_path, "json", None

    if suffix == ".onnx":
        from src.converter.onnx_to_json import convert_onnx_to_json

        if converted_json_output:
            converted_json_path = Path(converted_json_output).expanduser().resolve()
        else:
            converted_json_path = base_dir / "data" / "intermediate" / f"{input_model_path.stem}_from_onnx.json"
        convert_onnx_to_json(input_model_path, converted_json_path)
        return converted_json_path, "onnx", input_model_path

    raise ValueError(f"Unsupported input model format: {input_model_path.suffix}")


def _run_with_optional_stdout_capture(action, verbose: bool):
    if verbose:
        return action()

    captured_stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured_stdout):
            return action()
    except Exception:
        captured_output = captured_stdout.getvalue().strip()
        if captured_output:
            print(captured_output)
        raise


def main() -> None:
    args = _build_arg_parser().parse_args()
    base_dir = Path(__file__).resolve().parent
    split_output_dir = base_dir / "toolchain" / "pipeline_output" / "final_executable_config_split"
    link_input_dir = base_dir / "toolchain" / "pipeline_output" / "link_input"

    if args.input_final_config:
        original_final_config = Path(args.input_final_config).expanduser().resolve()
        final_file = _run_with_optional_stdout_capture(
            lambda: process_existing_final_config(final_config_file=original_final_config),
            verbose=args.verbose,
        )
        print("Parsing and validation completed")
        print("Input source type: final_config")
        print(f"Input final executable config: {original_final_config}")
        print(f"Final executable config: {Path(final_file).relative_to(base_dir)}")
        print(f"Split PE dataflow: {split_output_dir.relative_to(base_dir)}")
        print(f"Link input bundle: {link_input_dir.relative_to(base_dir)}")
        return

    input_json, input_source_type, original_input_model = _prepare_input_json(
        base_dir=base_dir,
        input_model=args.input_model,
        converted_json_output=args.converted_json_output,
    )

    ir_txt = base_dir / "data" / "intermediate" / "graph_ir.txt"
    output_json = base_dir / "data" / "output" / "graph.json"

    def _execute_model_pipeline() -> tuple[object, str]:
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
        return graph, final_file

    graph, final_file = _run_with_optional_stdout_capture(
        _execute_model_pipeline,
        verbose=args.verbose,
    )

    print("Parsing and validation completed")
    print(f"Input source type: {input_source_type}")
    if original_input_model is not None:
        print(f"Input ONNX: {original_input_model}")
    else:
        print(f"Input JSON: {input_json}")
    print(f"Final executable config: {Path(final_file).relative_to(base_dir)}")
    print(f"Split PE dataflow: {split_output_dir.relative_to(base_dir)}")
    print(f"Link input bundle: {link_input_dir.relative_to(base_dir)}")


if __name__ == "__main__":
    main()
