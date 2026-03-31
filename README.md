# Merged Graph IR + Toolchain Project

## 项目说明

本工程将 `src/` 中的计算图解析与 IR 生成流程，和 `toolchain/` 中的硬件映射与激励生成流程整合在一起。

主入口文件为 `main.py`。运行后可以根据输入类型，自动完成：

- 计算图解析
- IR 文本生成
- JSON 网络结构生成
- toolchain 映射
- 最终激励 `final_executable_config.txt` 生成
- PE 配置拆分
- `link_input` 打包

## 环境准备

建议使用 Python 3.10 及以上版本。

安装依赖：

```bash
python -m pip install -r requirements.txt
```

当前 `requirements.txt` 中主要包含：

- `onnx>=1.19.1`

如果只使用 JSON 输入，通常不需要额外依赖；如果要使用 ONNX 输入，则需要安装 `onnx`。

## 实验入口

统一入口：

```bash
python main.py
```

默认只输出关键结果路径。

如果需要查看各阶段详细日志，可以使用：

```bash
python main.py --verbose
```

## 输入说明

当前代码支持 3 种输入方式。

### 1. 输入计算图 JSON

适用于已有原始网络描述 JSON 的情况。

运行方式：

```bash
python main.py --input-model "data/input/model.json"
```

如果不传参数，程序会默认优先查找：

1. `data/input/model.onnx`
2. `data/input/model.json`

也就是说：

- 若存在 `data/input/model.onnx`，默认按 ONNX 输入处理。
- 若不存在 `data/input/model.onnx`，则默认读取 `data/input/model.json`。

### 2. 输入 ONNX 计算图

适用于已有 ONNX 网络模型的情况。

运行方式：

```bash
python main.py --input-model "C:/Users/Admin/Desktop/xxx.onnx"
```

程序会先将 ONNX 自动转换成与当前工程原有格式一致的 JSON，再继续走后续流程。

如果需要指定 ONNX 转换后 JSON 的输出路径，可以使用：

```bash
python main.py --input-model "C:/Users/Admin/Desktop/xxx.onnx" --converted-json-output "data/intermediate/converted_from_onnx.json"
```

### 3. 输入完整激励文件 `final_executable_config.txt`

适用于前面映射流程已经完成，只想直接做后处理的情况。

运行方式：

```bash
python main.py --input-final-config "toolchain/pipeline_output/final_executable_config.txt"
```

此模式下会跳过以下阶段：

- 计算图解析
- IR 生成
- `graph.json` 生成
- `network_structure.json` 生成
- toolchain 前四个阶段

只保留以下后处理步骤：

- `final_executable_config.txt` 拆分
- `link_input` 打包

## 实验流程

### 当输入是 JSON 或 ONNX 时

程序执行流程如下：

1. 读取输入模型
2. 若输入为 ONNX，则先转换为 JSON
3. 生成中间 IR：`graph_ir.txt`
4. 将 IR 转换为 `graph.json`
5. 复制为 toolchain 输入文件 `network_structure.json`
6. 调用 toolchain 生成完整激励 `final_executable_config.txt`
7. 自动拆分 PE 配置，输出 `final_executable_config_split`
8. 自动打包后续链接输入目录 `link_input`

### 当输入是 `final_executable_config.txt` 时

程序执行流程如下：

1. 读取已有完整激励文件
2. 按规则拆分 PE 配置
3. 生成 `link_input`

## 输出说明

### 一、中间输出

当输入是 JSON 或 ONNX 时，会生成以下中间文件：

- `data/intermediate/graph_ir.txt`
  计算图对应的 IR 文本

- `data/output/graph.json`
  由 IR 转换得到的 JSON 网络结构

- `toolchain/network_structure.json`
  提供给 toolchain 使用的网络结构文件

- `data/intermediate/<onnx文件名>_from_onnx.json`
  仅在输入为 ONNX 时生成，表示 ONNX 转换后的 JSON

### 二、toolchain 输出

输出目录：

- `toolchain/pipeline_output/`

其中主要包括：

- `1_original_tasks.txt`
  原始任务指令

- `1_aligned_tasks.txt`
  地址对齐后的任务指令

- `2_control_and_tasks.txt`
  控制模块与任务信息

- `3_full_config_with_data.txt`
  拼接数据后的完整配置

- `task_addresses.json`
  任务地址信息

- `data_addresses.json`
  数据地址信息

- `final_executable_config.txt`
  最终完整激励文件

### 三、PE 拆分输出

输出目录：

- `toolchain/pipeline_output/final_executable_config_split/`

程序会从 `final_executable_config.txt` 中自动提取每个任务的 PE 配置，并按任务分别输出。

目录结构示例：

```text
toolchain/pipeline_output/final_executable_config_split/
  1/
    dataflow/
      PE00.txt
      PE01.txt
      ...
  2/
    dataflow/
      PE00.txt
      PE01.txt
      ...
```

说明：

- 当前只在 `dataflow/` 中保存 PE 配置
- `insflow/` 不存放内容
- 池化任务会在拆分时被剔除
- 剩余任务会重新连续编号输出

### 四、链接输入输出

输出目录：

- `toolchain/pipeline_output/link_input/`

该目录用于后续链接流程输入，内部包含：

- `final_executable_config.txt`
- `final_executable_config_split/`

其中：

- `final_executable_config.txt` 为链接阶段使用的激励文件
- `final_executable_config_split/` 为对应任务的 PE 配置拆分结果

## 常用运行示例

### 示例 1：使用默认输入运行

```bash
python main.py
```

### 示例 2：使用 JSON 输入运行

```bash
python main.py --input-model "data/input/model.json"
```

### 示例 3：使用 ONNX 输入运行

```bash
python main.py --input-model "C:/Users/Admin/Desktop/Resnet640_cifar10_no_Normalize_int0810.onnx"
```

### 示例 4：直接输入完整激励运行

```bash
python main.py --input-final-config "toolchain/pipeline_output/final_executable_config.txt"
```

## 当前主入口文件

- `main.py`：统一输入入口
- `src/converter/onnx_to_json.py`：ONNX 转 JSON
- `src/service/pipeline.py`：计算图解析与 IR 生成
- `toolchain/stage5_main.py`：toolchain 总流程与后处理调用
