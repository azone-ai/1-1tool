from __future__ import annotations

import shutil
from pathlib import Path


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

    shutil.copy2(final_config_path, bundle_path / final_config_path.name)
    shutil.copytree(split_output_path, bundle_path / split_output_path.name)

    print(f"Link input bundle created: {bundle_path}")
    return bundle_path
