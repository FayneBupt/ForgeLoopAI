import json
import re
from pathlib import Path
from typing import Any, Dict, List

class ProjectWorkspace:
    def __init__(self, root: Path, local_profile: Dict[str, Any] = None):
        self.root = root
        self.projects_root = root / 'projects'
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.local_profile = local_profile or {}
        self.agent_name = self.local_profile.get("agent_name", "IDE Agent")
        self.process_user = self.local_profile.get("process_user", "$(whoami)")

    def project_dir(self, name: str) -> Path:
        return self.projects_root / name

    def init_project(self, name: str) -> Dict[str, Any]:
        pdir = self.project_dir(name)
        if pdir.exists():
            return {
                "status": "error",
                "message": f"项目 {name} 已存在，不能重复初始化"
            }
        pdir.mkdir(parents=True, exist_ok=True)

        config_path = pdir / 'config.json'
        config = {
            "project_name": name,
            "project_path": "/path/to/your/project_source",
            "goal": "在这里填写本次开发或修复的目标，例如：修复湖仓读取 Null 指针异常",
            "max_tries_per_round": 3,
            "history_context": [],
            "log_directories": [
                "/path/to/project_source/output/fe/log",
                "/path/to/project_source/output/be/log"
            ],
            "build_commands": [
                "echo '执行编译操作...'",
                "docker exec <YOUR_DOCKER_CONTAINER> /bin/bash -lc 'cd /path/to/project_source && bash build.sh --be -j8'"
            ],
            "stop_commands": [
                "cd /path/to/Lakehouse-Sandbox-Cluster && docker-compose down || true",
                "cd /path/to/Doris-Dev-Runner && ./stop_doris.sh /path/to/project_source/output || true",
                f"timeout 60s bash -c 'while ps -ef | grep \"[d]oris_\" | grep {self.process_user} >/dev/null; do echo \"等待 Doris 进程完全退出...\"; sleep 2; done' || true",
                f"ps -ef | grep doris | grep {self.process_user} | grep -v grep | awk '{{print $2}}' | xargs -r kill -9 || true"
            ],
            "clean_commands": [
                "echo '清理历史日志和元数据，确保干净启动...'",
                "rm -rf /path/to/project_source/output/fe/log/*",
                "rm -rf /path/to/project_source/output/be/log/*",
                "rm -rf /path/to/project_source/output/fe/doris-meta/*",
                "rm -rf /path/to/project_source/output/be/storage/*"
            ],
            "deploy_commands": [
                "cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker-compose up -d",
                "echo '等待 Hive Metastore (9083) 启动...'",
                "timeout 120s bash -c 'until sudo docker exec paimon-hive-metastore bash -c \"</dev/tcp/127.0.0.1/9083\" 2>/dev/null; do sleep 3; done'",
                "cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker cp init.sql paimon-flink-jobmanager:/tmp/init.sql && sudo docker exec paimon-flink-jobmanager ./bin/sql-client.sh -f /tmp/init.sql",
                "grep -q 'paimon-namenode' /etc/hosts || echo '127.0.0.1 paimon-namenode paimon-datanode paimon-hive-metastore' | sudo tee -a /etc/hosts",
                "echo '启动 Doris FE...'",
                "cd /path/to/project_source/output/fe && export JAVA_HOME=\"/path/to/Doris-Dev-Runner/jdk17\" && export PATH=\"$JAVA_HOME/bin:$PATH\" && unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && bash bin/start_fe.sh --daemon",
                "echo '启动 Doris BE...'",
                "cd /path/to/project_source/output/be && export JAVA_HOME=\"/path/to/Doris-Dev-Runner/jdk17\" && export PATH=\"$JAVA_HOME/bin:$PATH\" && unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && bash bin/start_be.sh --daemon"
            ],
            "check_commands": [
                "echo '等待 Doris FE(9040) 与 BE(9060) 端口就绪，最长等待 120 秒...'",
                "timeout 120s bash -c 'until nc -z 127.0.0.1 9040 2>/dev/null; do echo \"等待 FE...\"; sleep 3; done'",
                "timeout 120s bash -c 'until nc -z 127.0.0.1 9060 2>/dev/null; do echo \"等待 BE...\"; sleep 3; done'",
                "echo '服务端口已打开，尝试注册 BE 节点...'",
                "mysql -h 127.0.0.1 -P 9040 -uroot -e \"ALTER SYSTEM ADD BACKEND '127.0.0.1:9060';\" 2>/dev/null || true",
                "echo '检查 FE/BE 进程心跳状态 (Alive: true)...'",
                "timeout 120s bash -c 'until mysql -h 127.0.0.1 -P 9040 -uroot -e \"SHOW FRONTENDS;\" 2>/dev/null | grep -q \"true\"; do echo \"等待 FE 心跳正常...\"; sleep 3; done'",
                "timeout 120s bash -c 'until mysql -h 127.0.0.1 -P 9040 -uroot -e \"SHOW BACKENDS;\" 2>/dev/null | grep -q \"true\"; do echo \"等待 BE 心跳正常...\"; sleep 3; done'",
                "echo '心跳检查通过！验证 BE 计算组是否真正 Ready (等待可用 Backends)...'",
                "timeout 120s bash -c 'until mysql -h 127.0.0.1 -P 9040 -uroot -e \"SELECT 1;\" 2>/dev/null | grep -q \"1\"; do echo \"等待计算节点完全初始化...\"; sleep 3; done'",
                "echo 'BE 计算节点完全就绪！'",
                "mysql -h 127.0.0.1 -P 9040 -uroot -e \"SHOW FRONTENDS\\G; SHOW BACKENDS\\G;\"",
                "echo '输出最新启动日志供 AI 参考...'",
                "tail -n 20 /path/to/project_source/output/fe/log/fe.log",
                "tail -n 20 /path/to/project_source/output/be/log/be.INFO"
            ],
            "test_commands": [
                "echo '==== 开始执行环境测试 (Test) ===='",
                "echo '[Test 1/3] 重建 Catalog (paimon_hive_catalog)...'",
                "mysql -h 127.0.0.1 -P 9040 -uroot -e \"DROP CATALOG IF EXISTS paimon_hive_catalog; CREATE CATALOG paimon_hive_catalog PROPERTIES('type'='paimon','paimon.catalog.type'='hms','hive.metastore.uris'='thrift://127.0.0.1:9083','warehouse'='hdfs://127.0.0.1:8020/paimon/warehouse');\"",
                "echo '[Test 2/3] 验证表结构是否可查...'",
                "mysql -h 127.0.0.1 -P 9040 -uroot -e \"SWITCH paimon_hive_catalog; USE doris_paimon_db; SHOW TABLES;\"",
                "echo '[Test 3/3] 验证预置数据是否能正常读取...'",
                "mysql -h 127.0.0.1 -P 9040 -uroot -e \"SWITCH paimon_hive_catalog; USE doris_paimon_db; SELECT * FROM doris_insert_test ORDER BY id LIMIT 10;\"",
                "echo '==== 环境测试完毕，具备回归验证条件 ===='"
            ],
            "verify_cases": [
                {
                    "name": "Case 1: 开启 Paimon JNI Writer",
                    "description": "测试 enable_paimon_jni_writer=true 时的写入和读取",
                    "sql": "SET enable_paimon_jni_writer=true; SWITCH paimon_hive_catalog; USE doris_paimon_db; INSERT INTO doris_insert_test VALUES (1001,'from_doris_insert_case_jni_true','2026-04-03'); SELECT * FROM doris_insert_test ORDER BY id DESC LIMIT 20;"
                },
                {
                    "name": "Case 2: 关闭 Paimon JNI Writer",
                    "description": "测试 enable_paimon_jni_writer=false 时的写入和读取",
                    "sql": "SET enable_paimon_jni_writer=false; SWITCH paimon_hive_catalog; USE doris_paimon_db; INSERT INTO doris_insert_test VALUES (1002,'from_doris_insert_case_jni_false','2026-04-03'); SELECT * FROM doris_insert_test ORDER BY id DESC LIMIT 20;"
                }
            ]
        }
        self._write_json(config_path, config)
        return {
            "status": "success",
            "message": f"项目 {name} 初始化成功",
            "project_dir": str(pdir),
            "config_file": str(config_path)
        }

    def _format_cases_for_prompt(self, cases: List[Dict[str, Any]]) -> str:
        if not cases:
            return "无"
        lines = []
        for i, c in enumerate(cases, 1):
            lines.append(f"  - [Case {i}] {c.get('name', '未命名')}: {c.get('description', '无描述')}")
        return "\n".join(lines)

    def generate_mission(self, name: str) -> Dict[str, Any]:
        pdir = self.project_dir(name)
        if not pdir.exists():
            return {"status": "error", "message": f"项目 {name} 不存在，请先执行 init"}
            
        config_path = pdir / 'config.json'
        if not config_path.exists():
            return {"status": "error", "message": "找不到 config.json，请检查项目目录"}
            
        config = self._read_json(config_path)
        
        history_context = config.get("history_context", [])
        history_text = ""
        if not history_context:
            history_text = "- 无历史轮次，这是你第一次接手该任务。"
        else:
            lines = []
            for idx, data in enumerate(history_context):
                r_num = data.get("round", idx + 1)
                status = data.get("status", "UNKNOWN")
                bugs = data.get("bugs_found", "无")
                fixes = data.get("fixes_applied", "无")
                lines.append(f"- 历史战役 {r_num} | 状态: {status} | Bugs: {bugs} | Fixes: {fixes}")
            history_text = "\n".join(lines)
            
        def _format_cmds(cmds: Any) -> str:
            if not cmds:
                return "无"
            if isinstance(cmds, list):
                return "\n".join(f"  - {cmd}" for cmd in cmds)
            return f"  - {cmds}"

        # Dynamically generate the && chained command example based on config
        example_cmds = []
        for key in ['build_commands', 'stop_commands', 'clean_commands', 'deploy_commands', 'check_commands', 'test_commands']:
            cmds = config.get(key, [])
            if cmds:
                example_cmds.extend(cmds)
        
        # Add verify_cases to example cmds
        verify_cases = config.get('verify_cases', [])
        if verify_cases:
            example_cmds.append("bash scripts/stage7_verify.sh")

        if example_cmds:
            # We don't want duplicate test_commands if we already added it via test_cases compilation
            # Let's clean up any potential duplication by converting to set but keeping order
            seen = set()
            clean_cmds = []
            for cmd in example_cmds:
                if cmd not in seen:
                    clean_cmds.append(cmd)
                    seen.add(cmd)
            chained_example = " && ".join(clean_cmds)
        else:
            chained_example = "bash stage1_build.sh && bash stage2_stop.sh && bash stage3_clean.sh && bash stage4_deploy.sh && bash stage5_check.sh && bash stage6_test.sh && bash stage7_verify.sh"

        loop_definition = f"【完整测试闭环】包含以下严格顺序：编译 -> 停止服务 -> 清理环境 -> 部署服务 -> 部署后检查 -> 环境测试 -> 核心验证。\n（提示：为了减少网络交互轮数，你可以使用 `&&` 将所有阶段的命令拼接成一行，一次性交给终端执行。例如：\n`{chained_example}`）"
        max_tries = config.get('max_tries_per_round', 3)

        if not history_context:
            workflow_steps = f'''1. {loop_definition}
2. **切勿急着修改代码！** 请先直接执行一次【完整测试闭环】。在大多数情况下，它会在“核心验证”或某个阶段失败，你的首要任务是拿到这个最原始的报错日志。
3. **分析与修改**：根据第 2 步的报错日志（请善用前面的日志排查指引），结合本轮总体目标，开始修改源码。
4. **验证修复**：代码修改完成后，再次执行【完整测试闭环】。
5. **重试与意外中止机制**：如果依然报错，你可以继续“查看日志 -> 修改代码 -> 执行完整闭环”。但请注意：
   - 在本次对话中，你最多只能进行 **{max_tries} 次** 这样的尝试。
   - 如果遇到**意外情况**（例如：无法获取核心报错日志、环境严重卡死、反复出现相同的不可理喻的错误、缺乏有效反馈继续推进），你必须**立刻主动中止**。
6. 满足以下任一条件时必须停止工作：
   - 成功通过了“核心验证”：输出 SUCCEEDED 报告。
   - 达到了 {max_tries} 次重试上限：输出 FAILED 报告。
   - 触发了意外中止机制：输出 FAILED 报告，并在 bugs_found 中详细描述这个阻碍你继续的“意外情况”。'''
        else:
            workflow_steps = f'''1. 仔细阅读【前情提要】，了解前人遗留的问题和历史尝试。
2. {loop_definition}
3. **第一步绝不允许直接修改代码！** 你必须先无脑执行一次【完整测试闭环】。因为接手时环境状态未知，你必须通过这次执行，拿到属于你当前视角的、最新鲜的报错日志。
4. **分析与修改**：拿到最新报错后，结合前人的教训，开始修改源码。
5. **验证修复**：代码修改完成后，重新执行【完整测试闭环】。
6. **重试与意外中止机制**：如果依然报错，你可以继续“查看日志 -> 修改代码 -> 执行完整闭环”。但请注意：
   - 在本次对话中，你最多只能进行 **{max_tries} 次** 这样的尝试。
   - 如果遇到**意外情况**（例如：无法获取核心报错日志、环境严重卡死、反复出现相同的不可理喻的错误、缺乏有效反馈继续推进），你必须**立刻主动中止**。
7. 满足以下任一条件时必须停止工作：
   - 成功通过了“核心验证”：输出 SUCCEEDED 报告。
   - 达到了 {max_tries} 次重试上限：输出 FAILED 报告。
   - 触发了意外中止机制：输出 FAILED 报告，并在 bugs_found 中详细描述这个阻碍你继续的“意外情况”。'''

        log_dirs = config.get('log_directories', [])
        if log_dirs:
            log_guide = "【日志排查指引（重要）】\n如果在任何阶段遇到报错（例如 `check` 或 `verify` 阶段抛出异常），你需要自主查看以下日志目录下的文件定位问题：\n"
            for d in log_dirs:
                log_guide += f"- {d} (主要查看 fe.log, fe.out, fe.warn.log, be.INFO, be.out, be.WARNING 等)\n"
            log_guide += "（提示：善用 `grep -C 10 -i \"Exception\" <log_file>` 或直接读取文件尾部获取堆栈信息。）\n"
        else:
            log_guide = ""

        knowledge_path = self.root.parent / 'knowledge.md'
        knowledge_guide = ""
        if knowledge_path.exists():
            knowledge_text = knowledge_path.read_text(encoding='utf-8').strip()
            if knowledge_text:
                knowledge_guide = f"【开发与调试注意点（非常重要）】\n{knowledge_text}\n"

        test_cases = config.get('test_cases', [])
        if test_cases:
            test_section = f"环境测试用例集（自动编译为 scripts/stage6_test.sh，请直接执行 bash scripts/stage6_test.sh）：\n{self._format_cases_for_prompt(test_cases)}"
        else:
            test_section = f"环境测试命令（用于确认测试环境已就绪，请按顺序执行）：\n{_format_cmds(config.get('test_commands', []))}"

        prompt = f'''你是 {self.agent_name}，当前任务是协助我完成代码的开发、编译、部署与测试闭环。

【项目上下文】
代码路径：{config.get('project_path', '/')}
本轮总体目标：{config.get('goal', '无')}

{log_guide}
{knowledge_guide}
编译命令（请按顺序执行）：
{_format_cmds(config.get('build_commands', []))}

停止服务命令（请按顺序执行）：
{_format_cmds(config.get('stop_commands', []))}

清理环境命令（请按顺序执行）：
{_format_cmds(config.get('clean_commands', []))}

部署服务命令（请按顺序执行）：
{_format_cmds(config.get('deploy_commands', []))}

部署后检查命令（请按顺序执行）：
{_format_cmds(config.get('check_commands', []))}

{test_section}

核心验证用例集（自动编译为 scripts/stage7_verify.sh，请直接执行 bash scripts/stage7_verify.sh）：
{self._format_cases_for_prompt(config.get('verify_cases', []))}

【前情提要】
{history_text}

【你的工作流（严格遵守）】
{workflow_steps}

【收尾工作（必做）】
- 在本轮修改代码并测试（无论成功与否）后，**必须将你修改的所有代码提交一个 git commit**。请根据你修改的内容自行起一个合适的 commit message。
- 无论测试成功还是失败，**立刻停止工作**。绝不允许自行开启下一轮或进入死循环！

【任务输出与交接要求（极其重要）】
在结束本次战役时，你可以正常总结你的修复思路和结论。但**在回复的最后，你必须严格附上以下 JSON 格式的代码块**，以便系统进行自动收集和跨会话记忆接力（请确保只包含这一个合法的 JSON 块，并用 ```json 包裹）：

```json
{{
  "round": {len(history_context) + 1},
  "status": "SUCCEEDED或FAILED",
  "bugs_found": "遇到了什么问题，简要描述",
  "fixes_applied": "你是怎么解决的",
  "commits": "本轮你提交的 git commit hash 和 commit message",
  "token_usage": {{"prompt": 0, "completion": 0, "total": 0}}
}}
```

总结并输出上述 JSON 后，请告知我“本次任务执行完毕，报告已生成”，并请将该 JSON 内容保存到当前配置文件所在的目录下（即 `{pdir}` 目录），命名为 `history-<YYYYMMDDHHMMSS>.json`（请替换为当前的实际时间戳），然后结束当前对话。人类在 Review 后会自行决定是否将其纳入下一轮的上下文中。
'''

        prompt_path = pdir / 'mission.md'
        prompt_path.write_text(prompt, encoding='utf-8')
        
        return {
            "status": "success",
            "message": f"任务执行清单 mission.md 已生成",
            "prompt_file": str(prompt_path)
        }

    def rm_project(self, name: str) -> Dict[str, Any]:
        pdir = self.project_dir(name)
        if not pdir.exists():
            return {"status": "error", "message": f"项目 {name} 不存在"}
            
        import shutil
        try:
            shutil.rmtree(pdir)
            return {"status": "success", "message": f"项目 {name} 已成功删除"}
        except Exception as e:
            return {"status": "error", "message": f"删除项目 {name} 失败: {str(e)}"}

    def compile_scripts(self, name: str) -> Dict[str, Any]:
        pdir = self.project_dir(name)
        if not pdir.exists():
            return {"status": "error", "message": f"项目 {name} 不存在"}
            
        config_path = pdir / 'config.json'
        if not config_path.exists():
            return {"status": "error", "message": f"找不到 config.json"}
            
        config = self._read_json(config_path)
        scripts_dir = pdir / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        
        stage_map = {
            'build': ('stage1_build', 'build_commands'),
            'stop': ('stage2_stop', 'stop_commands'),
            'clean': ('stage3_clean', 'clean_commands'),
            'deploy': ('stage4_deploy', 'deploy_commands'),
            'check': ('stage5_check', 'check_commands'),
            'test': ('stage6_test', 'test_commands')
        }
        
        import stat
        for stage, (script_name, key) in stage_map.items():
            commands = config.get(key, [])
            if not commands:
                continue
                
            # If it's already a single bash script call, skip compiling
            if len(commands) == 1 and commands[0].startswith("bash ") and commands[0].endswith(f"{script_name}.sh"):
                continue
                
            script_path = scripts_dir / f"{script_name}.sh"
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write("#!/bin/bash\nset -e\n")
                for cmd in commands:
                    f.write(f"{cmd}\n")
            # add executable permission
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
            
            # replace config commands with script execution
            config[key] = [f"bash {script_path}"]
            
        mysql_port = config.get('mysql_port', 9040)
        
        # Handle test_cases similarly to verify_cases
        test_cases = config.get('test_cases', [])
        if test_cases:
            test_script_path = scripts_dir / "stage6_test.sh"
            with open(test_script_path, 'w', encoding='utf-8') as f:
                f.write("#!/bin/bash\n")
                f.write("success=0\n")
                f.write("fail=0\n\n")
                f.write("echo \"========== 开始执行环境测试集 (Test) ==========\"\n\n")
                
                for i, case in enumerate(test_cases, 1):
                    name = case.get('name', f'Test {i}')
                    desc = case.get('description', '')
                    sql = case.get('sql', '')
                    command = case.get('command', '')
                    
                    f.write("echo \"----------------------------------------\"\n")
                    f.write(f"echo \"👉 [{name}]\"\n")
                    f.write(f"echo \"📝 描述: {desc}\"\n")
                    if command:
                        f.write(f"if result=$({command} 2>&1); then\n")
                    else:
                        f.write(f"if result=$(mysql -h 127.0.0.1 -P {mysql_port} -uroot -e \"{sql}\" 2>&1); then\n")
                    f.write("    echo \"✅ 结果: SUCCESS\"\n")
                    f.write("    echo \"📊 输出:\"\n")
                    f.write("    echo \"$result\"\n")
                    f.write("    ((success++))\n")
                    f.write("else\n")
                    f.write("    echo \"❌ 结果: FAILED\"\n")
                    f.write("    echo \"📉 错误输出:\"\n")
                    f.write("    echo \"$result\"\n")
                    f.write("    ((fail++))\n")
                    f.write("fi\n\n")
                    
                f.write("echo \"----------------------------------------\"\n")
                f.write("echo \"========== 环境测试结果汇总 ==========\"\n")
                f.write(f"echo \"Total: {len(test_cases)}, Success: $success, Failed: $fail\"\n")
                f.write("if [ $fail -gt 0 ]; then\n")
                f.write("    exit 1\n")
                f.write("fi\n")
            
            test_script_path.chmod(test_script_path.stat().st_mode | stat.S_IEXEC)
            config['test_commands'] = [f"bash {test_script_path.absolute()}"]
            
        # Handle verify_cases separately
        verify_cases = config.get('verify_cases', [])
        if verify_cases:
            verify_script_path = scripts_dir / "stage7_verify.sh"
            with open(verify_script_path, 'w', encoding='utf-8') as f:
                f.write("#!/bin/bash\n")
                f.write("success=0\n")
                f.write("fail=0\n\n")
                f.write("echo \"========== 开始执行核心回归验证集 ==========\"\n\n")
                
                for i, case in enumerate(verify_cases, 1):
                    name = case.get('name', f'Case {i}')
                    desc = case.get('description', '')
                    sql = case.get('sql', '')
                    command = case.get('command', '')
                    
                    f.write("echo \"----------------------------------------\"\n")
                    f.write(f"echo \"👉 [{name}]\"\n")
                    f.write(f"echo \"📝 描述: {desc}\"\n")
                    if command:
                        f.write(f"if result=$({command} 2>&1); then\n")
                    else:
                        f.write(f"if result=$(mysql -h 127.0.0.1 -P {mysql_port} -uroot -e \"{sql}\" 2>&1); then\n")
                    f.write("    echo \"✅ 结果: SUCCESS\"\n")
                    f.write("    echo \"📊 输出:\"\n")
                    f.write("    echo \"$result\"\n")
                    f.write("    ((success++))\n")
                    f.write("else\n")
                    f.write("    echo \"❌ 结果: FAILED\"\n")
                    f.write("    echo \"📉 错误输出:\"\n")
                    f.write("    echo \"$result\"\n")
                    f.write("    ((fail++))\n")
                    f.write("fi\n\n")
                    
                f.write("echo \"----------------------------------------\"\n")
                f.write("echo \"========== 测试结果汇总 ==========\"\n")
                f.write(f"echo \"Total: {len(verify_cases)}, Success: $success, Failed: $fail\"\n")
                f.write("if [ $fail -gt 0 ]; then\n")
                f.write("    exit 1\n")
                f.write("fi\n")
            
            verify_script_path.chmod(verify_script_path.stat().st_mode | stat.S_IEXEC)
            config['verify_commands'] = [f"bash {verify_script_path.absolute()}"]

        self._write_json(config_path, config)
        return {"status": "success", "message": f"项目 {name} 的命令已成功编译并提取到 scripts 目录下！"}

    def project_status(self, name: str = None) -> Dict[str, Any]:
        if name:
            projects = [self.project_dir(name)]
            if not projects[0].exists():
                return {"status": "error", "message": f"项目 {name} 不存在"}
        else:
            projects = [p for p in self.projects_root.iterdir() if p.is_dir()]
            
        results = []
        import datetime
        for pdir in projects:
            pname = pdir.name
            
            # get creation time of config.json
            config_path = pdir / 'config.json'
            if config_path.exists():
                stat_info = config_path.stat()
                created_at = datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_at = "UNKNOWN"

            mission_path = pdir / 'mission.md'
            mission_path_str = str(mission_path) if mission_path.exists() else "Not generated"

            results.append({
                "project": pname,
                "created_at": created_at,
                "config_path": str(config_path),
                "mission_path": mission_path_str
            })
            
        return {"status": "success", "projects": results}

    def run_stage(self, name: str, stage: str) -> int:
        pdir = self.project_dir(name)
        if not pdir.exists():
            print(f"[Error] 项目 {name} 不存在")
            return 1
            
        config_path = pdir / 'config.json'
        if not config_path.exists():
            print(f"[Error] 找不到 config.json")
            return 1
            
        config = self._read_json(config_path)

        stage = stage.strip()
        if ',' in stage:
            raw_stages = [s.strip() for s in stage.split(',') if s.strip()]
        else:
            raw_stages = [stage] if stage else []

        if not raw_stages:
            print("[Error] run 阶段参数为空，请至少传入一个阶段。")
            return 1

        valid_stages = {'build', 'stop', 'clean', 'deploy', 'check', 'test', 'verify', 'all', 'all-no-build'}
        for s in raw_stages:
            if s not in valid_stages:
                print(f"[Error] 非法阶段: {s}")
                print(f"[Hint] 支持阶段: {', '.join(sorted(valid_stages))}")
                return 1

        stage_sequences = {
            'all': ['build', 'stop', 'clean', 'deploy', 'check', 'test', 'verify'],
            'all-no-build': ['stop', 'clean', 'deploy', 'check', 'test', 'verify']
        }
        expanded_stages = []
        for s in raw_stages:
            if s in stage_sequences:
                expanded_stages.extend(stage_sequences[s])
            else:
                expanded_stages.append(s)

        if len(expanded_stages) > 1:
            print(f"\n=======================================================")
            print(f" 开始按序执行生命周期阶段 | Project: [{name}]")
            print(f" 阶段流转: {' -> '.join(expanded_stages)}")
            print(f"=======================================================\n")

        for s in expanded_stages:
            code = self._execute_single_stage(name, pdir, config, s)
            if code != 0:
                print(f"\n[Fatal] 生命周期测试在 [{s}] 阶段失败退出！")
                return code

        if len(expanded_stages) > 1:
            print("\n[Success] 生命周期阶段按顺序执行成功！")
        return 0

    def _execute_single_stage(self, name: str, pdir: Path, config: Dict[str, Any], stage: str) -> int:
        stage_map = {
            'build': ('stage1_build', 'build_commands'),
            'stop': ('stage2_stop', 'stop_commands'),
            'clean': ('stage3_clean', 'clean_commands'),
            'deploy': ('stage4_deploy', 'deploy_commands'),
            'check': ('stage5_check', 'check_commands'),
            'test': ('stage6_test', 'test_commands'),
            'verify': ('stage7_verify', 'verify_commands')
        }
        
        script_name, key = stage_map.get(stage, (stage, ''))
        commands = config.get(key, [])
        if not commands:
            print(f"[Warn] 阶段 '{script_name}' 没有配置任何命令。")
            return 0
            
        import subprocess
        print(f"========== 开始测试执行 {name} 的 [{script_name}] 阶段 ==========")
        for i, cmd in enumerate(commands, 1):
            print(f"\n>>> [{script_name}] 第 {i} 步: {cmd}")
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    executable="/bin/bash",
                    cwd=config.get("project_path", str(pdir))
                )
                if result.returncode != 0:
                    print(f"\n[Error] 命令执行失败，退出码: {result.returncode}")
                    return result.returncode
            except Exception as e:
                print(f"\n[Error] 命令执行异常: {str(e)}")
                return 1
                
        print(f"\n========== [{script_name}] 阶段执行成功！ ==========\n")
        return 0

    def _extract_round_num(self, filename: str) -> int:
        match = re.search(r'round_(\d+)\.(json|pending)', filename)
        return int(match.group(1)) if match else 99999

    def _write_json(self, path: Path, obj: Any) -> None:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding='utf-8'))
