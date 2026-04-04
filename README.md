# 🚀 ForgeLoopAI v1.0

![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![IDE](https://img.shields.io/badge/IDE-Trae%20Solo%20Coder-purple.svg)

**ForgeLoopAI** 是一个专为 IDE Agent（例如 Trae 的 Solo Coder）设计的 **极简开发上下文与 Prompt 管理器**。

在面对 Apache Doris 等重型 C++ / Java / Rust 大型开源工程时，IDE Agent 常常会：
- 🤯 **记不住复杂的构建/部署环境**（比如几十行的 `cmake` 或 `docker compose` 指令）
- 🔄 **陷入死循环**（遇到编译报错疯狂盲目重试，直到耗尽上下文）
- 🗑️ **开发状态混乱**（挂机跑了一晚上，完全不知道它解决了什么、提交了什么、消耗了多少 Token）

**ForgeLoopAI 彻底摒弃了传统 CI/CD 沉重的 Pipeline 架构。** 
它通过「本地文件记录」和「单轮强约束 Prompt 生成」的机制，将复杂的开发流程降维成 **1个配置文件** 和 **3个极简命令**。

---

## ✨ 核心特性

- **📂 纯本地文件系统管理**：无需数据库、无 Daemon 服务。一切状态均记录在你当前目录的 `runtime/` 中，Git 友好。
- **🧩 组合命令管理**：将 `build` / `deploy` / `test` 的多行 Bash 命令统一托管，每次发给 AI 前自动注入。
- **🛑 单轮防失控机制**：通过精心调优的 Prompt 模版，强行约束 AI 执行「编译->部署->测试->修复」的单轮闭环后必须立即停止工作。
- **🔀 智能多轮续接**：自动区分首轮与多轮 Prompt。在多轮迭代中，工具会自动抓取上一轮的报错点，让 AI 从失败处无缝接手。
- **📝 强制 Git 提交**：在 Prompt 中严格约束 AI 每轮结束前必须提交 Git Commit，保留完整的开发足迹，随时可以回滚。
- **📊 自动战况汇总**：AI 工作完成后会按要求将成果（Bug、Fix、Commit 记录、Token）写入本地 JSON，你可以随时在终端通过动态宽度的漂亮表格一览无余。

---

## 🛠️ 快速安装

```bash
git clone https://github.com/your-username/ForgeLoopAI.git
cd ForgeLoopAI

# 推荐以可编辑模式全局安装
pip install -e .

# 配置 alias (可选)
alias fl='forgeloop'
```

---

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
> 在生成 Prompt 交给 AI 执行之前，**你必须自己手动验证 `config.json` 中的每一个生命周期命令！**
> AI 是根据你提供的命令原封不动去执行的。如果你给的构建脚本路径不对、或者部署命令本身就会报语法错误，AI 就会一直在这些低级错误上浪费 Token 并陷入死循环。**确保基建命令绝对正确，是 AI 能帮你修复代码逻辑 Bug 的大前提。**
> 
> 为了方便你验证，ForgeLoopAI 提供了一键测试工具：
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

### 2. 生成 Prompt (推动 AI 工作)
```bash
forgeloop push doris_bug_123
```
执行后，工具会扫描历史记录，并生成包含「前情提要」和「严格契约」的 `prompt_round_1.md`。

**👉 你的动作：** 
打开该 Markdown 文件，全选复制，直接发给 Trae 的 Solo Coder 对话框。然后去喝杯咖啡。☕

> *在 Prompt 中，Trae 被要求执行完一轮后，将总结自动写回 `runtime/projects/doris_bug_123/history/round_1.json`。*

### 3. 查看全局战况
当你回到工位，只需要敲：
```bash
forgeloop status
```
你就能看到清爽的进度表格（支持超长项目名自适应）：
```text
项目名称                                  | 轮次   | 消耗Tokens   | 最新状态            
-----------------------------------------------------------------------------------------
doris_bug_123                             | 1      | 2450         | FAILED
a_very_long_project_name_for_testing      | 5      | 15000        | SUCCEEDED
```

### 4. 查看具体轮次明细
如果上一轮失败了，想看看 AI 到底踩了什么坑：
```bash
forgeloop show doris_bug_123
```
工具会直接打印出 AI 每轮发现的 Bug、做的修改、本轮的 Git 提交记录以及 Token 消耗明细。
然后你只需再次执行 `forgeloop push doris_bug_123`，工具会把之前的失败记录打包成前情提要，开启全新的第 2 轮！

---

## 🐳 最佳实践：编写健壮的 config.json
在配合 AI 工作时，你的 Bash 脚本如果不健壮，AI 就会反复失败。强烈建议参考以下原则编写 `config.json`：

1. **不要无脑 `sleep`，用 `timeout + until` 轮询**
   如果服务 2 秒就起好了，`sleep 15` 就是浪费时间；如果机器卡了 20 秒才起好，`sleep 15` 就会导致后面的命令直接失败。
   ✅ *正确写法：*
   ```json
   "timeout 120s bash -c 'until nc -z 127.0.0.1 9040 2>/dev/null; do echo \"等待 FE...\"; sleep 3; done'"
   ```

2. **屏蔽无用的探测错误日志（保护 Token）**
   探测期间连不上引发的 `Connection refused` 报错会被大模型全盘吸收，不仅浪费 Token，还会让大模型产生“有严重 Bug”的幻觉。
   ✅ *正确写法：在可能频繁报错的探测命令后加上 `2>/dev/null`*
   ```json
   "timeout 120s bash -c 'until mysql -e \"SELECT 1;\" 2>/dev/null | grep -q \"1\"; do sleep 3; done'"
   ```

3. **环境拆分：Test 与 Verify 隔离**
   在 `test_commands` 中，只放基础环境的连通性测试（比如创建数据库、查询基础表）；在 `verify_commands` 中，再放具体的业务验证（如重现你修好的 Bug）。这能极大帮助 AI 缩小排错范围。

---

## 🐳 进阶应用：搭配极简湖仓沙盒

在进行诸如 Apache Doris 湖仓一体（Lakehouse）相关的开发或 Bug 修复时，往往需要一个包含 HDFS、Hive Metastore 等组件的底层环境。

推荐搭配使用 [Lakehouse-Sandbox-Cluster](https://github.com/FayneBupt/Lakehouse-Sandbox-Cluster) —— 一个专为测试和开发湖仓组件设计的极简、开箱即用的 Docker Compose 沙盒。

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

---

## 🧹 其他命令

如果你修完了 Bug 且代码已经 Merge，想清理掉这个项目的运行时历史：
```bash
forgeloop rm doris_bug_123
```

---

## 🤝 贡献与参与

这个项目目前定位为面向个人开发者的极简工具。如果你有更好的 Prompt 约束技巧或者希望增加对其他 IDE（如 Cursor / Windsurf）的预设模版，欢迎提交 Pull Request！

**License:** MIT
