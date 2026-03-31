# 图 IR 与硬件工具链合并项目

本项目把 `src/` 中的图结构解析流程，与 `toolchain/` 中的硬件激励生成流程整合在一起。程序的目标是从网络结构描述文件出发，依次生成图 IR、中间 JSON、硬件任务配置、最终二进制激励文件，以及后续链接阶段所需的拆分目录。

当前主入口为 `main.py`。默认情况下，只需要准备好输入网络结构和工具链资源，执行一次 `python main.py` 即可完成整条处理链。

## 1. 项目用途

这个程序主要完成以下工作：

1. 读取 `data/input/model.json` 中的网络结构描述。
2. 对网络结构做基础合法性校验。
3. 生成中间 IR 文本 `graph_ir.txt`。
4. 再将 IR 转成 JSON，供后续工具链继续使用。
5. 调用 `toolchain/` 内的多阶段流程，生成完整硬件激励。
6. 从最终激励 `final_executable_config.txt` 中自动拆分出每个任务对应的 PE 配置文件。
7. 将“原始最终激励文件”和“拆分后的任务目录”重新打包到同一个目录中，作为后续链接工作的输入。

## 2. 目录说明

项目中比较关键的目录和文件如下：

- `main.py`
  主程序入口，负责串联图 IR 生成和工具链执行。
- `data/input/model.json`
  默认输入网络结构文件。
- `data/intermediate/`
  保存中间 IR 文本。
- `data/output/`
  保存由 IR 转换得到的 JSON 结果。
- `src/`
  图结构解析、校验、IR 生成、TXT 转 JSON 等逻辑。
- `toolchain/`
  硬件激励生成主流程及各阶段脚本。
- `toolchain/Op_Library/`
  算子激励库，阶段 1 用它匹配任务指令模板。
- `toolchain/Data_Library/`
  数据库资源，阶段 3 用它匹配权重和输出数据。
- `toolchain/pipeline_output/`
  工具链执行后的输出目录。
- `tests/`
  测试目录。

## 3. 运行方式

本工程当前依赖 Python 标准库即可运行，`requirements.txt` 中没有额外第三方依赖说明。

执行方式：

```bash
python main.py
```

程序默认读取：

```text
data/input/model.json
```

如果后续需要适配别的网络结构，通常修改这个文件即可。

## 4. 主流程总览

`main.py` 的执行顺序可以概括为下面 3 个大阶段：

1. 图结构校验与 IR 生成。
2. 工具链多阶段激励生成。
3. 最终激励拆分与链接输入打包。

对应的处理链路如下：

```text
model.json
  -> graph_ir.txt
  -> graph.json
  -> toolchain/network_structure.json
  -> final_executable_config.txt
  -> final_executable_config_split/
  -> link_input/
```

## 5. 程序详细执行过程

### 5.1 图结构处理阶段

这部分主要由 `src/service/pipeline.py` 和 `src/converter/txt_to_json.py` 完成。

处理逻辑如下：

1. 读取 `data/input/model.json`。
2. 校验顶层数据是否为列表，每个算子是否为字典结构。
3. 对每个算子的字段进行合法性校验。
4. 解析得到图结构对象。
5. 对整个图做图级校验。
6. 生成文本形式的中间 IR，输出到 `data/intermediate/graph_ir.txt`。
7. 将 IR 文本再次转换为 JSON，输出到 `data/output/graph.json`。

这一步的结果相当于把原始模型结构规范化成工具链更容易消费的格式。

### 5.2 工具链输入准备

在 `main.py` 中，生成的 `data/output/graph.json` 会被复制到：

```text
toolchain/network_structure.json
```

后续 `toolchain/` 的所有阶段都以这个文件作为网络结构输入。

### 5.3 工具链阶段 1：任务指令生成与对齐

文件：

```text
toolchain/stage1_task_generator.py
```

主要职责：

1. 读取 `toolchain/network_structure.json`。
2. 从 `toolchain/Op_Library/` 中加载算子模板。
3. 根据网络层类型匹配合适的算子激励文件 `op_jili.txt`。
4. 按任务粒度拆分网络层：
   - `Conv` 层按输出通道分任务，每 10 个输出通道一个任务。
   - `FC` 层按输出特征分任务，每 10 个输出特征一个任务。
   - `Pool` 层固定生成 1 个任务。
5. 生成原始任务文件 `1_original_tasks.txt`。
6. 对任务块做地址对齐，生成 `1_aligned_tasks.txt`。

这一步的核心，是把网络层拆成硬件可以逐任务执行的指令块。

### 5.4 工具链阶段 2：控制模块与 FIFO 信息生成

文件：

```text
toolchain/stage2_control_generator.py
```

主要职责：

1. 读取对齐后的任务文件。
2. 重新识别每个任务的起始行和指令条数。
3. 生成任务地址映射 `task_addresses.json`。
4. 生成 FIFO 描述信息。
5. 构造前 1536 行控制区。
6. 将控制区与任务区合并，输出 `2_control_and_tasks.txt`。

这一步的结果，是把“控制器信息”和“任务指令信息”拼接成统一配置文件。

### 5.5 工具链阶段 3：数据链接

文件：

```text
toolchain/stage3_data_linker.py
```

主要职责：

1. 读取 `toolchain/Data_Library/` 中的算子数据资源。
2. 匹配每个任务需要的权重数据和输出数据。
3. 为第一层生成输入数据块。
4. 将任务文件、输入数据、权重数据、输出数据拼接为完整文件。
5. 记录数据地址映射到 `data_addresses.json`。
6. 输出 `3_full_config_with_data.txt`。

这一步相当于把“可执行指令”和“执行所需数据”真正链接在一起。

### 5.6 工具链阶段 4：最终地址修正

文件：

```text
toolchain/stage4_address_modifier.py
```

主要职责：

1. 读取 `task_addresses.json` 与 `data_addresses.json`。
2. 扫描任务区内以 `011` 开头的存储控制配置。
3. 根据输入、权重、输出三类数据的实际地址，回填配置中的地址字段。
4. 输出最终激励文件：

```text
toolchain/pipeline_output/final_executable_config.txt
```

到这一步，主激励文件已经具备后续执行所需的完整地址信息。

### 5.7 工具链阶段 6：自动拆分 PE 配置

文件：

```text
toolchain/stage6_dataflow_exporter.py
```

这是本次新增的重要功能，用来把最终激励自动拆成后续流程需要的任务目录。

拆分规则如下：

1. 从 `final_executable_config.txt` 的第 513 行开始，读取任务索引表。
2. 每行固定为 128 位二进制字符串。
3. 从每行最后往前看：
   - 倒数 32 位表示该任务的行数。
   - 再往前 32 位表示任务起始地址。
4. 任务真实起始行计算方式为：

```text
实际起始行 = 起始地址 / 16 + 1
```

5. 根据“实际起始行 + 任务行数”定位当前任务的内容范围。
6. 在任务范围内，只连续提取以 `001` 开头的行，视为 PE 配置区。
7. 这些连续的 `001...` 行中，最后一行是启动配置，不参与导出，需要剔除。
8. 剩余内容每两行作为一个 PE 配置单元。
9. 每两行 128 位配置再拆成四行 64 位文本。
10. 输出到任务目录下的 `dataflow/PE*.txt`。
11. 同时创建 `insflow/` 目录，但当前不写入任何内容。

生成目录结构示意如下：

```text
toolchain/pipeline_output/final_executable_config_split/
  ├─ 1/
  │   ├─ dataflow/
  │   │   ├─ PE00.txt
  │   │   ├─ PE01.txt
  │   │   └─ ...
  │   └─ insflow/
  ├─ 2/
  │   ├─ dataflow/
  │   └─ insflow/
  └─ ...
```

说明：

- 目前程序实际输出文件名从 `PE00.txt` 开始编号。
- `insflow/` 仅保留目录结构，不写入文件。

### 5.8 工具链阶段 7：链接输入目录打包

文件：

```text
toolchain/stage7_link_input_packager.py
```

这是本次新增的第二个关键功能，用来把后续链接阶段需要的两类输入放到同一个目录中。

打包结果目录为：

```text
toolchain/pipeline_output/link_input/
```

其中包含：

1. `final_executable_config.txt`
2. `final_executable_config_split/`

也就是说，后续链接阶段如果需要同时使用“完整激励文件”和“拆分后的任务目录”，可以直接把 `link_input/` 作为统一输入目录。

## 6. 运行后会生成哪些文件

执行 `python main.py` 后，常见输出包括：

- `data/intermediate/graph_ir.txt`
- `data/output/graph.json`
- `toolchain/network_structure.json`
- `toolchain/pipeline_output/1_original_tasks.txt`
- `toolchain/pipeline_output/1_aligned_tasks.txt`
- `toolchain/pipeline_output/2_control_and_tasks.txt`
- `toolchain/pipeline_output/3_full_config_with_data.txt`
- `toolchain/pipeline_output/task_addresses.json`
- `toolchain/pipeline_output/data_addresses.json`
- `toolchain/pipeline_output/final_executable_config.txt`
- `toolchain/pipeline_output/final_executable_config_split/`
- `toolchain/pipeline_output/link_input/`

## 7. 当前默认输入模型说明

当前默认输入文件是：

```text
data/input/model.json
```

从现有内容来看，模型包含：

- 多层卷积 `Conv`
- 池化层 `Pool`
- 一层全连接 `FC`

因此，当前流程已经覆盖了 `Conv`、`Pool`、`FC` 三类算子处理逻辑。

## 8. 关键入口文件

如果后续还需要继续扩展功能，建议优先关注以下文件：

- `main.py`
  总入口，负责串联全流程。
- `src/service/pipeline.py`
  图结构校验与 IR 生成入口。
- `src/converter/txt_to_json.py`
  IR 文本转 JSON。
- `toolchain/stage5_main.py`
  工具链总调度入口。
- `toolchain/stage6_dataflow_exporter.py`
  最终激励拆分逻辑。
- `toolchain/stage7_link_input_packager.py`
  链接输入目录打包逻辑。

## 9. 一句话总结

这个项目现在已经形成了一条完整链路：从网络结构描述出发，自动生成最终硬件激励，并进一步拆分出每个任务的 PE `dataflow` 文件，同时把完整激励和拆分结果统一打包为后续链接工作的输入目录。
