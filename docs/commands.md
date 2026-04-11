# ForgeLoopAI 命令大全

## 基础命令

### `forgeloop init <project_name>`
- 作用：初始化项目目录与 `config.json` 模板
- 示例：

```bash
forgeloop init doris_bug_123
```

### `forgeloop status [project_name]`
- 作用：查看所有项目或指定项目状态
- 示例：

```bash
forgeloop status
forgeloop status doris_bug_123
```

### `forgeloop mission <project_name>`
- 作用：生成本轮 `mission.md`
- 示例：

```bash
forgeloop mission doris_bug_123
```

### `forgeloop rm <project_name>`
- 作用：删除项目目录及运行时历史
- 示例：

```bash
forgeloop rm doris_bug_123
```

## 执行命令

### `forgeloop run <project_name> <stage>`
- 作用：执行生命周期阶段
- `stage` 支持：
  - `build`
  - `stop`
  - `clean`
  - `deploy`
  - `check`
  - `test`
  - `verify`
  - `all`
  - `all-no-build`
- 支持逗号按序执行：

```bash
forgeloop run doris_bug_123 stop,clean,deploy
```

### `--build-target`（仅 build 阶段生效）
- 可选值：`all` / `be` / `fe`
- 作用：控制 build 只编译 BE、只编译 FE 或全量
- 示例：

```bash
forgeloop run doris_bug_123 build --build-target all
forgeloop run doris_bug_123 build --build-target be
forgeloop run doris_bug_123 build --build-target fe
forgeloop run doris_bug_123 all --build-target be
```

### 独立脚本执行与环境变量注入
- ForgeLoopAI 的生命周期脚本现在已与 CLI **彻底解耦**。你可以随时脱离 `fl run` 直接执行 `scripts/stage*.sh` 脚本。
- 脚本执行时会自动向上寻找 `config.local.json` 并将其中的 `env` 字段作为操作系统的**原生环境变量**注入，实现了隐私隔离和随处可用的灵活性。
- 示例：

```bash
bash runtime/projects/doris_bug_123/scripts/stage1_build.sh
FL_BUILD_TARGET=be bash runtime/projects/doris_bug_123/scripts/stage1_build.sh
```

## 调试与工具

### `forgeloop debug <project_name>`
- 作用：自动采集 FE / BE JNI / BE GDB 堆栈
- 输出：`runtime/projects/<project_name>/debug-<timestamp>/`
- 示例：

```bash
forgeloop debug doris_bug_123
```

### `forgeloop start <script> [-- <args...>]`
- 作用：执行 `runtime/projects/tools` 下的 Python 工具脚本（如压测脚本、发压器等）
- 自动透传 `SEC_TOKEN_STRING` 鉴权信息。
- `script` 支持省略 `.py` 后缀
- 示例：

```bash
forgeloop start start_with_auth -- --host 127.0.0.1 --port 9045 --loops 1
```

## 核心验证阶段与 SQL 自动断言 (@EXPECT / @VERIFY)

在执行 `stage7_verify` 阶段时，系统会按字母顺序遍历 `scripts/sql/*.sql` 文件。为了实现自动化测试验证和预期判断，我们在 SQL 注释中引入了一套**轻量级断言引擎**。

### 控制指令 (@VERIFY)
在 `.sql` 文件的**第一行**写入以下注释，可以控制该测试用例是否被执行：
- **`-- @VERIFY: SKIP`** 或 **`-- @VERIFY: DISABLE`**：跳过当前文件的执行。
- **`-- @VERIFY: ENABLE`**：正常执行（默认行为，可不写）。

### 断言指令 (@EXPECT)
在任何一条具体的 SQL 语句（包括 `SELECT`、`INSERT` 等）的**正上方**写入 `-- @EXPECT: <TYPE> [VALUE]`，引擎会在该条 SQL 执行完毕后自动进行断言比对：

#### 1. 预期抛出异常 (`EXCEPTION`)
用于测试负向用例（如脏数据插入、主键冲突等）。
- 语法：`-- @EXPECT: EXCEPTION <keyword>`
- 行为：断言该 SQL **必须**抛出异常，且异常的错误信息中必须包含 `<keyword>`（忽略大小写）。如果 SQL 执行成功未报错，或报错信息不包含该关键字，则断言失败。
- 示例：
```sql
-- 插入脏数据，预期报错
-- @EXPECT: EXCEPTION mismatch on partition key
INSERT OVERWRITE TABLE paimon_1.t1 PARTITION(dt='20240101', hh='10') VALUES (1, 'a', '20240101', '11');
```

#### 2. 预期结果行数 (`ROW_COUNT`)
用于验证返回的结果集行数或受影响的行数。
- 语法：`-- @EXPECT: ROW_COUNT <num>`
- 行为：断言查询结果的行数为 `<num>`。
- 示例：
```sql
-- 期望只查出 2 条数据
-- @EXPECT: ROW_COUNT 2
SELECT * FROM paimon_1.t1;
```

#### 3. 预期精确结果集 (`RESULT`)
用于严格比对查询返回的每一行数据内容。
- 语法：
```sql
-- @EXPECT: RESULT
-- <row_1_data>
-- <row_2_data>
```
- 行为：断言结果集必须与下方注释中提供的数据**完全一致**（逗号分隔，自动忽略前后的空格）。如果行数或内容不匹配，则断言失败。
- 示例：
```sql
-- @EXPECT: RESULT
-- 1000, new_a, 1, 20240101
-- 2000, new_b, 2, 20240102
SELECT * FROM paimon_1.t1 ORDER BY c1;
```

#### 4. 预期无结果 (`NONE` 或 `EMPTY`)
用于断言表中无数据或条件不匹配。
- 语法：`-- @EXPECT: NONE` 或 `-- @EXPECT: EMPTY`
- 行为：断言结果集行数必须为 0。
- 示例：
```sql
-- @EXPECT: NONE
SELECT * FROM paimon_1.t1 WHERE 1=0;
```

## 配置建议

- 在 `config.local.json` 中配置个人的私有变量（如 `DORIS_PORT`, `DORIS_PROJECT_PATH`），并通过 `$VAR` 在 `stage*.sh` 脚本中直接读取。
- 首轮或环境变化后优先全量编译 `all`，仅改 BE/FE 时使用对应的 `--build-target`。

## 文档维护约定

- 每次新增或修改 CLI 命令、参数、默认行为或断言引擎时，必须同步更新本文件。