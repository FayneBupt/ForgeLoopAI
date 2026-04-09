# 🚀 ForgeLoopAI v1.0

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![IDE](https://img.shields.io/badge/IDE-AI%20Agent-purple.svg)](#)

**ForgeLoopAI** 是一个专为 AI-Native 软件工程打造的 **极简 7 阶段沙盒测试引擎与任务调度器**。

在面对 Apache Doris 等重型 C++ / Java / Rust 大型开源工程时，IDE Agent 或 CLI Agent 常常会：

- 🤯 **记不住复杂的构建/部署环境**（比如几十行的 `cmake` 或 `docker compose` 指令）
- 🔄 **陷入死循环**（遇到编译报错疯狂盲目重试，直到耗尽上下文）
- 🗑️ **被脏日志污染产生幻觉**（满屏的连通性报错让 AI 误以为代码有严重 Bug）

**ForgeLoopAI 彻底摒弃了传统 CI/CD 沉重的 Pipeline 架构，也摒弃了需要人类不断“多轮 Push”的保姆式交互。**
它通过将整个测试生命周期脚本化，构建了一个极其严苛的 **“单轮强力闭环与自循环优化”** 机制。AI 在接到一次任务（Mission）后，会在其单次会话上下文内疯狂执行 `修改代码 -> 跑 7 阶段脚本 -> 精准获取报错 -> 再次修改` 的内部迭代，直到成功或触发兜底中止机制。

***

## ✨ 核心特性

- **📂 纯本地文件系统管理**：无需数据库、无 Daemon 服务。一切状态均沉淀在你当前目录的 `config.json` 中。
- **🧩 7 阶段沙盒闭环**：强制将工程拆分为 `build -> stop -> clean -> deploy -> check -> test -> verify` 七个独立阶段，为 AI 提供极致干净、每次都幂等的执行温床。
- **🛑 强力自循环与防死锁机制**：通过精心调优的终极任务清单（`mission.md`），赋予 AI 自主循环试错的权利，同时设定严格的重试上限（如 `max_tries_per_round: 3`）和意外中止兜底，防止烧光 Token。
- **🔀 跨会话的记忆接力**：当 AI 达到重试上限或意外卡死时，会输出标准化的 JSON 历史报告（`history-timestamp.json`）。人类可按需将其沉淀入 `config.json`，下一任 AI 接手时将自动继承前人的排坑经验（降维打击）。
- **📝 强制 Git 提交**：在 Prompt 中严格约束 AI 在修改测试后必须提交 Git Commit，保留完整的开发足迹。
- **📊 极简状态追踪**：随时在终端通过动态宽度的漂亮表格一览无余项目的状态和配置位置。

***

## 🛠️ 快速安装

```bash
git clone https://github.com/<your-org-or-username>/ForgeLoopAI.git
cd ForgeLoopAI

# 推荐以可编辑模式全局安装
pip install -e .

# 配置 alias (可选)
alias fl='forgeloop'
```

***

## 🔒 本地化配置（脱敏）

如果你希望仓库保持通用模板，但本地保留自己的个性化信息（比如 Agent 名称、进程用户名），可以这样做：

```bash
cp forgeloop.local.example.json forgeloop.local.json
```

然后编辑 `forgeloop.local.json`：

```json
{
  "agent_name": "你的 IDE Agent 名称",
  "process_user": "你的系统用户名或$(whoami)"
}
```

- `forgeloop.local.json` 已在 `.gitignore` 中，**不会被提交到 GitHub**
- `forgeloop.local.example.json` 会提交到仓库，作为团队共享模板

***

## 🚀 3分钟快速上手

我们以修复一个叫 `doris_bug_123` 的任务为例：

### 1. 初始化项目与任务配置

```bash
forgeloop init doris_bug_123
```

这会在当前目录下生成 `runtime/projects/doris_bug_123/config.json`。
打开这个文件，填入你的代码路径、业务目标以及复杂的组合命令：

> ⚠️ **极其重要（必读）**
>
> 在生成 Prompt 交给 AI 执行之前，**你必须自己手动验证** **`config.json`** **中的每一个生命周期命令！**
> AI 是根据你提供的命令原封不动去执行的。如果你给的构建脚本路径不对、或者部署命令本身就会报语法错误，AI 就会一直在这些低级错误上浪费 Token 并陷入死循环。**确保基建命令绝对正确，是 AI 能帮你修复代码逻辑 Bug 的大前提。**
>
> 为了方便你验证，ForgeLoopAI 提供了一键测试工具：
>
> ```bash
> # 比如你想验证你的部署命令是否能跑通：
> forgeloop run doris_bug_123 deploy
>
> # 支持测试的阶段包括：build / stop / clean / deploy / check / test / verify
>
> # 或者直接按顺序跑通整个生命周期，验证无缝衔接：
> forgeloop run doris_bug_123 all
>
> # 因为大型 C++ 项目编译太耗时，如果只想测试部署到测试的全流程：
> forgeloop run doris_bug_123 all-no-build
> ```

```json
{
  "project_name": "doris_bug_123",
  "project_path": "/data/doris/source",
  "goal": "修复湖仓读取 Parquet 的 Null 指针异常，必须通过所有回归测试",
  "build_commands": [
    "export SKIP_CONTRIB_SUBMODULE_UPDATE=1",
    "bash build.sh --be -j8"
  ],
  "stop_commands": [
    "bash stop.sh"
  ],
  "clean_commands": [
    "rm -rf logs/*"
  ],
  "deploy_commands": [
    "docker compose -f docker-compose.yaml up -d"
  ],
  "check_commands": [
    "curl http://127.0.0.1:8080/health"
  ],
  "test_commands": [
    "bash prepare-env.sh"
  ],
  "verify_commands": [
    "bash run-regression-test.sh"
  ]
}
```

### 2. 生成 Mission (推动 AI 工作)

```bash
forgeloop mission doris_bug_123
```

执行后，工具会扫描 `config.json` 中的 `history_context`，并生成包含「前情提要」和「严格契约」的终极任务清单 `mission.md`。

你可以直接将 `mission.md` 的内容复制给你的 IDE Agent，或者通过 Aider 等 CLI Agent 直接执行：

```bash
# 假设结合 Aider 使用
aider --message-file runtime/projects/doris_bug_123/mission.md
```

### 3. 跨会话接力与降维打击

AI 在达到最大重试次数或意外中止时，会按要求在项目目录下输出一段名为 `history-<YYYYMMDDHHMMSS>.json` 的报告文件。

如果它失败了，你想更换更强的大模型继续推进：

1. 打开它生成的 `history-xxx.json`。
2. 将这段 JSON 内容复制并追加到你 `config.json` 的 `history_context` 数组中。
3. 重新执行 `forgeloop mission doris_bug_123`。
4. 新生成的 `mission.md` 就会自动将前人的失败经验总结为【前情提要】，让新接手的大模型直接站在前人的肩膀上降维打击！

### 4. 查看全局状态

当你回到工位，只需要敲：

```bash
forgeloop status
```

你就能看到类似 MySQL `\G` 的清爽状态信息，方便复制和阅读长路径：

```text
*************************** 1. row ***************************
       Project: doris_bug_123
    Created At: 2026-04-04 12:00:00
   Config Path: /path/to/runtime/projects/doris_bug_123/config.json
  Mission Path: /path/to/runtime/projects/doris_bug_123/mission.md
1 rows in set
```

***

## 🐳 最佳实践：编写健壮的 config.json

在配合 AI 工作时，你的 Bash 脚本如果不健壮，AI 就会反复失败。强烈建议参考以下原则编写 `config.json`：

1. **不要无脑** **`sleep`，用** **`timeout + until`** **轮询**
   如果服务 2 秒就起好了，`sleep 15` 就是浪费时间；如果机器卡了 20 秒才起好，`sleep 15` 就会导致后面的命令直接失败。
   ✅ *正确写法：*
   ```json
   "timeout 120s bash -c 'until nc -z 127.0.0.1 9040 2>/dev/null; do echo \"等待 FE...\"; sleep 3; done'"
   ```
2. **屏蔽无用的探测错误日志（保护 Token）**
   探测期间连不上引发的 `Connection refused` 报错会被大模型全盘吸收，不仅浪费 Token，还会让大模型产生“有严重 Bug”的幻觉。
   ✅ *正确写法：在可能频繁报错的探测命令后加上* *`2>/dev/null`*
   ```json
   "timeout 120s bash -c 'until mysql -e \"SELECT 1;\" 2>/dev/null | grep -q \"1\"; do sleep 3; done'"
   ```
3. **环境拆分：Test 与 Verify 隔离**
   在 `test_commands` 中，只放基础环境的连通性测试（比如创建数据库、查询基础表）；在 `verify_commands` 中，再放具体的业务验证（如重现你修好的 Bug）。这能极大帮助 AI 缩小排错范围。

***

## 🐳 进阶应用：搭配极简湖仓沙盒

在进行诸如 Apache Doris 湖仓一体（Lakehouse）相关的开发或 Bug 修复时，往往需要一个包含 HDFS、Hive Metastore 等组件的底层环境。

推荐搭配使用 [Lakehouse-Sandbox-Cluster](https://github.com/<your-org-or-username>/Lakehouse-Sandbox-Cluster) —— 一个专为测试和开发湖仓组件设计的极简、开箱即用的 Docker Compose 沙盒。

你可以将其一键集成到 ForgeLoopAI 的 `config.json` 中作为前置依赖：

```json
{
  "deploy_commands": [
    "cd /path/to/Lakehouse-Sandbox-Cluster && docker-compose up -d",
    "sleep 15",
    "docker cp init.sql paimon-flink-jobmanager:/tmp/init.sql",
    "docker exec paimon-flink-jobmanager ./bin/sql-client.sh -f /tmp/init.sql"
  ]
}
```

这样，AI 在执行测试前就会自动拉起 HDFS + Hive Metastore + Flink，并准备好测试表与数据，为你提供一个完美的最小化外围环境。

***

## 🐳 进阶应用：自动化提取脚本 (compile)

当你的 `config.json` 越写越复杂（包含了长串的 Docker 启动命令和心跳检测时），让 AI 一行一行粘贴执行很容易出错（比如漏掉分号、管道符截断等）。
你可以使用 `compile` 命令，将配置中的所有内联命令**一键提取并固化**为独立的 `.sh` 脚本：

```bash
forgeloop compile doris_bug_123
```

执行后：

1. 框架会在项目目录下自动生成一个 `scripts` 文件夹。
2. 为每个生命周期生成独立的脚本（如 `build.sh`, `deploy.sh`, `check.sh`），并自动在文件头部注入 `#!/bin/bash` 和 `set -e`。
3. 你的 `config.json` 会被自动替换为类似 `"deploy_commands": ["bash /path/to/.../scripts/deploy.sh"]`。

**优势：** 彻底隔离“控制面”和“执行面”。AI 只需执行一句简单的 `bash deploy.sh`，内部复杂的逻辑闭环都在本地高速执行，再也不用担心上下文截断和拷贝错误！

***

## 🧹 其他命令

如果你修完了 Bug 且代码已经 Merge，想清理掉这个项目的运行时历史：

```bash
forgeloop rm doris_bug_123
```

***

## 🤝 贡献与参与

这个项目目前定位为面向个人开发者的极简工具。如果你有更好的 Prompt 约束技巧或者希望增加对其他 IDE（如 Cursor / Windsurf）的预设模版，欢迎提交 Pull Request！

**License:** MIT
