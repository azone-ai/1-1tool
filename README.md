# Merged Graph IR + Toolchain Project

This project combines the graph IR flow in `src/` with the hardware toolchain in `toolchain/`.

## Run

```bash
python main.py
```

## Outputs

Running `main.py` generates:

- `data/intermediate/graph_ir.txt`
- `data/output/graph.json`
- `toolchain/network_structure.json`
- `toolchain/pipeline_output/final_executable_config.txt`
- `toolchain/pipeline_output/final_executable_config_split/<task_id>/dataflow/PE*.txt`

The split export is produced automatically from `final_executable_config.txt`:

- task descriptors are parsed from line 513 onward
- the last consecutive `001...` line in each task is treated as the startup config and skipped
- every two remaining `001...` lines are split into four 64-bit lines and written into `dataflow`
- `insflow` directories are created but left empty
