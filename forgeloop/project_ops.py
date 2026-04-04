import json
import re
from pathlib import Path
from typing import Any, Dict, List

class ProjectWorkspace:
    def __init__(self, root: Path):
        self.root = root
        self.projects_root = root / 'projects'
        self.projects_root.mkdir(parents=True, exist_ok=True)

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
        history_dir = pdir / 'history'
        history_dir.mkdir(exist_ok=True)

        config_path = pdir / 'config.json'
        config = {
            "project_name": name,
            "project_path": "/path/to/your/project_source",
            "goal": "在这里填写本次开发或修复的目标，例如：修复湖仓读取 Null 指针异常",
            "build_commands": [
                "echo '执行编译操作...'",
                "sudo docker exec <YOUR_DOCKER_CONTAINER> /bin/bash -lc 'cd /path/to/project_source && bash build.sh --be -j8'"
            ],
            "stop_commands": [
                "cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker-compose down || true",
                "cd /path/to/Doris-Dev-Runner && ./stop_doris.sh /path/to/project_source/output || true",
                "timeout 60s bash -c 'while ps -ef | grep \"[d]oris_\" | grep <YOUR_USERNAME> >/dev/null; do echo \"等待 Doris 进程完全退出...\"; sleep 2; done' || true"
            ],
            "clean_commands": [
                "echo '清理历史日志和元数据，确保干净启动...'",
                "rm -rf /path/to/Doris-Dev-Runner/log/fe/*",
                "rm -rf /path/to/Doris-Dev-Runner/log/be/*",
                "rm -rf /path/to/project_source/output/fe/doris-meta/*",
                "rm -rf /path/to/project_source/output/be/storage/*"
            ],
            "deploy_commands": [
                "cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker-compose up -d",
                "echo '等待 Hive Metastore (9083) 启动...'",
                "timeout 120s bash -c 'until sudo docker exec paimon-hive-metastore bash -c \"</dev/tcp/127.0.0.1/9083\" 2>/dev/null; do sleep 3; done'",
                "cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker cp init.sql paimon-flink-jobmanager:/tmp/init.sql && sudo docker exec paimon-flink-jobmanager ./bin/sql-client.sh -f /tmp/init.sql",
                "grep -q 'paimon-namenode' /etc/hosts || echo '127.0.0.1 paimon-namenode paimon-datanode paimon-hive-metastore' | sudo tee -a /etc/hosts",
                "cd /path/to/Doris-Dev-Runner && ./start_doris.sh /path/to/project_source/output"
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
                "tail -n 20 /path/to/Doris-Dev-Runner/log/fe/fe.log",
                "tail -n 20 /path/to/Doris-Dev-Runner/log/be/be.INFO"
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
            "verify_commands": [
                "echo '==== 开始核心回归验证 (Verify) ===='",
                "echo '[Verify 1/1] 执行 INSERT INTO 操作并查询验证结果...'",
                "mysql -h 127.0.0.1 -P 9040 -uroot -e \"SWITCH paimon_hive_catalog; USE doris_paimon_db; INSERT INTO doris_insert_test VALUES (1001,'from_doris_insert_case','2026-04-03'); SELECT * FROM doris_insert_test ORDER BY id DESC LIMIT 20;\"",
                "echo '==== 核心回归验证完毕 ===='"
            ]
        }
        self._write_json(config_path, config)
        return {
            "status": "success",
            "message": f"项目 {name} 初始化成功",
            "project_dir": str(pdir),
            "config_file": str(config_path)
        }

    def push_project(self, name: str) -> Dict[str, Any]:
        pdir = self.project_dir(name)
        if not pdir.exists():
            return {"status": "error", "message": f"项目 {name} 不存在，请先执行 init"}
            
        config_path = pdir / 'config.json'
        if not config_path.exists():
            return {"status": "error", "message": "找不到 config.json，请检查项目目录"}
            
        config = self._read_json(config_path)
        
        history_dir = pdir / 'history'
        history_dir.mkdir(exist_ok=True)
        
        # 扫描 history/*.json，确定当前是第几轮
        round_files = list(history_dir.glob("round_*.json"))
        history_data = []
        for rf in sorted(round_files, key=lambda x: self._extract_round_num(x.name)):
            try:
                data = self._read_json(rf)
                r_num = data.get("round", self._extract_round_num(rf.name))
                history_data.append((r_num, data))
            except Exception:
                pass
                
        history_data.sort(key=lambda x: x[0])
        next_round = len(history_data) + 1
        
        history_text = ""
        if not history_data:
            history_text = "- 无历史轮次，这是第 1 轮。"
        else:
            lines = []
            for r_num, data in history_data:
                status = data.get("status", "UNKNOWN")
                bugs = data.get("bugs_found", "无")
                fixes = data.get("fixes_applied", "无")
                lines.append(f"- 第 {r_num} 轮 | 状态: {status} | Bugs: {bugs} | Fixes: {fixes}")
            history_text = "\n".join(lines)
            
        history_json_target = str((history_dir / f"round_{next_round}.json").absolute())

        def _format_cmds(cmds: Any) -> str:
            if not cmds:
                return "无"
            if isinstance(cmds, list):
                return "\n".join(f"  - {cmd}" for cmd in cmds)
            return f"  - {cmds}"

        if next_round == 1:
            workflow_steps = f'''1. 分析本轮目标，开始修改代码。
2. 执行【编译命令】。若失败，请定位日志并修复代码，然后再次编译，直到编译成功或你认为无法继续。
3. 执行【停止服务命令】。确保旧服务已停止。
4. 执行【清理环境命令】。删除历史日志，排除干扰。
5. 执行【部署服务命令】。拉起新编译的服务。
6. 执行【部署后检查命令】。确认服务正常拉起，若有报错请立刻查看新生成的日志并尝试修复。
7. 执行【环境测试命令】。确保系统具备验证 Bug 的基础能力（如成功创建建表、导入数据等）。
8. 执行【核心验证命令】。跑业务测试用例，验证你的修复或开发是否真正满足了本轮目标。'''
        else:
            workflow_steps = f'''1. 仔细阅读前情提要。从上一轮失败的地方（如编译报错、测试不通过等）开始接手，继续修改和修复代码。
2. 如果上一轮是编译失败，修复代码后继续执行【编译命令】；如果是部署或测试失败，确保重新编译。
3. 依次执行【停止服务命令】、【清理环境命令】、【部署服务命令】、【部署后检查命令】，确保服务重新干净拉起。若再次失败，请定位日志并修复代码，循环直到成功或无法继续。
4. 确保最终执行并验证【环境测试命令】和【核心验证命令】。'''

        prompt = f'''你是 Trae Solo Coder，当前任务是协助我完成代码的开发、编译、部署与测试闭环。

【项目上下文】
代码路径：{config.get('project_path', '/')}
本轮总体目标：{config.get('goal', '无')}

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

环境测试命令（用于确认测试环境已就绪，请按顺序执行）：
{_format_cmds(config.get('test_commands', []))}

核心验证命令（用于验证修复或目标是否真正完成，请按顺序执行）：
{_format_cmds(config.get('verify_commands', []))}

【前情提要】
当前是第 {next_round} 轮。
历史记录如下：
{history_text}

【你的工作流（严格遵守）】
{workflow_steps}

【收尾工作（必做）】
- 在本轮修改代码并测试（无论成功与否）后，**必须将你修改的所有代码提交一个 git commit**。请根据你修改的内容自行起一个合适的 commit message。
- 无论测试成功还是失败，**立刻停止工作**。绝不允许自行开启下一轮或进入死循环！

【本轮输出要求（极其重要）】
工作停止后，你必须将本轮的执行结果，严格按照以下 JSON 格式，**直接保存到文件** `{history_json_target}` 中（请直接将内容写入文件，不要只输出在对话框里）：

```json
{{
  "round": {next_round},
  "status": "SUCCEEDED或FAILED",
  "bugs_found": "遇到了什么问题，简要描述",
  "fixes_applied": "你是怎么解决的",
  "commits": "本轮你提交的 git commit hash 和 commit message",
  "token_usage": {{"prompt": 0, "completion": 0, "total": 0}}
}}
```

写完文件后，请直接对我说“第 {next_round} 轮执行完毕，报告已生成”，并结束当前对话。
'''

        prompt_path = pdir / f'prompt_round_{next_round}.md'
        prompt_path.write_text(prompt, encoding='utf-8')
        
        # 记录一个正在进行中的状态标记
        pending_marker = history_dir / f'round_{next_round}.pending'
        pending_marker.touch()
        
        return {
            "status": "success",
            "message": f"第 {next_round} 轮 Prompt 已生成",
            "prompt_file": str(prompt_path),
            "next_round": next_round
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

    def project_status(self, name: str = None) -> Dict[str, Any]:
        if name:
            projects = [self.project_dir(name)]
            if not projects[0].exists():
                return {"status": "error", "message": f"项目 {name} 不存在"}
        else:
            projects = [p for p in self.projects_root.iterdir() if p.is_dir()]
            
        results = []
        for pdir in projects:
            pname = pdir.name
            history_dir = pdir / 'history'
            round_files = list(history_dir.glob("round_*.json")) if history_dir.exists() else []
            
            history_data = []
            for rf in round_files:
                try:
                    data = self._read_json(rf)
                    r_num = data.get("round", self._extract_round_num(rf.name))
                    history_data.append((r_num, data))
                except Exception:
                    pass
            history_data.sort(key=lambda x: x[0])
            
            total_tokens = sum(
                int(data.get("token_usage", {}).get("total", 0))
                for _, data in history_data
            )
            
            last_status = "UNKNOWN"
            current_rounds = len(history_data)
            
            # 检查是否有正在进行的下一轮
            pending_files = list(history_dir.glob("round_*.pending")) if history_dir.exists() else []
            if pending_files:
                # 找到最大的 pending 轮次
                pending_nums = [self._extract_round_num(pf.name) for pf in pending_files]
                max_pending = max(pending_nums)
                if max_pending > current_rounds:
                    current_rounds = max_pending - 1
                    last_status = f"RUNNING (Round {max_pending})"
                elif history_data:
                    last_status = history_data[-1][1].get("status", "UNKNOWN")
            elif history_data:
                last_status = history_data[-1][1].get("status", "UNKNOWN")
                
            results.append({
                "project": pname,
                "rounds": current_rounds,
                "total_tokens": total_tokens,
                "last_status": last_status
            })
            
        return {"status": "success", "projects": results}

    def show_project(self, name: str) -> Dict[str, Any]:
        pdir = self.project_dir(name)
        if not pdir.exists():
            return {"status": "error", "message": f"项目 {name} 不存在"}
            
        history_dir = pdir / 'history'
        round_files = list(history_dir.glob("round_*.json")) if history_dir.exists() else []
        
        history_data = []
        for rf in round_files:
            try:
                data = self._read_json(rf)
                r_num = data.get("round", self._extract_round_num(rf.name))
                history_data.append((r_num, data))
            except Exception:
                pass
        history_data.sort(key=lambda x: x[0])
        
        return {"status": "success", "project": name, "history": [h[1] for h in history_data]}

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

        if stage in ('all', 'all-no-build'):
            if stage == 'all':
                stages = ['build', 'stop', 'clean', 'deploy', 'check', 'test', 'verify']
            else:
                stages = ['stop', 'clean', 'deploy', 'check', 'test', 'verify']
                
            print(f"\n=======================================================")
            print(f" 开始执行完整生命周期测试 | Project: [{name}]")
            print(f" 阶段流转: {' -> '.join(stages)}")
            print(f"=======================================================\n")
            for s in stages:
                code = self._execute_single_stage(name, pdir, config, s)
                if code != 0:
                    print(f"\n[Fatal] 完整生命周期测试在 [{s}] 阶段失败退出！")
                    return code
            print(f"\n[Success] 完整生命周期测试成功通过！你可以放心地生成 Prompt 交给 AI 了。")
            return 0
        else:
            return self._execute_single_stage(name, pdir, config, stage)

    def _execute_single_stage(self, name: str, pdir: Path, config: Dict[str, Any], stage: str) -> int:
        stage_map = {
            'build': 'build_commands',
            'stop': 'stop_commands',
            'clean': 'clean_commands',
            'deploy': 'deploy_commands',
            'check': 'check_commands',
            'test': 'test_commands',
            'verify': 'verify_commands'
        }
        
        commands = config.get(stage_map.get(stage, ''), [])
        if not commands:
            print(f"[Warn] 阶段 '{stage}' 没有配置任何命令。")
            return 0
            
        import subprocess
        print(f"========== 开始测试执行 {name} 的 [{stage}] 阶段 ==========")
        for i, cmd in enumerate(commands, 1):
            print(f"\n>>> [{stage}] 第 {i} 步: {cmd}")
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
                
        print(f"\n========== [{stage}] 阶段执行成功！ ==========\n")
        return 0

    def _extract_round_num(self, filename: str) -> int:
        match = re.search(r'round_(\d+)\.(json|pending)', filename)
        return int(match.group(1)) if match else 99999

    def _write_json(self, path: Path, obj: Any) -> None:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding='utf-8'))
