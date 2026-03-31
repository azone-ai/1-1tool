# Merged Graph IR + Toolchain Project

该工程将两个代码目录合并为一个可运行项目：

1. `src/`：计算图解析、校验、生成 `graph_ir.txt`、再转换为 `graph.json`
2. `toolchain/`：保留 `stage1` 到 `stage5_main.py` 的工具链主流程，以及必需的 `Op_Library/`、`Data_Library/`

## 运行方式

```bash
python main.py
```

运行顺序：
- 读取 `data/input/model.json`
- 生成 `data/intermediate/graph_ir.txt`
- 生成 `data/output/graph.json`
- 将 `graph.json` 复制为 `toolchain/network_structure.json`
- 调用 `toolchain/stage5_main.py` 的 `run_pipeline()`
- 输出工具链结果到 `toolchain/pipeline_output/`

## 保留内容

保留了工具链主流程所需的核心代码：
- `stage1_task_generator.py`
- `stage2_control_generator.py`
- `stage3_data_linker.py`
- `stage4_address_modifier.py`
- `stage5_main.py`
- `Op_Library/`
- `Data_Library/`

未合并测试脚本、临时脚本、历史网络结构样例、IDE 配置等无关文件。
