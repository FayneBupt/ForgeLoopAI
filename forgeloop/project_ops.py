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
        pdir.mkdir(parents=True, exist_ok=True)
        history_dir = pdir / 'history'
        history_dir.mkdir(exist_ok=True)

        config_path = pdir / 'config.json'
        config = {
            "project_name": name,
            "project_path": "/path/to/your/project",
            "goal": "在这里填写本次开发或修复的目标，例如：修复湖仓读取 Null 指针异常",
            "build_commands": [
                "echo 'Running build step 1...'",
                "bash build.sh"
            ],
            "deploy_commands": [
                "echo 'Running deploy step 1...'",
                "docker compose up -d"
            ],
            "test_commands": [
                "echo 'Running test step 1...'",
                "bash run-test.sh"
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

        prompt = f'''你是 Trae Solo Coder，当前任务是协助我完成代码的开发、编译、部署与测试闭环。

【项目上下文】
代码路径：{config.get('project_path', '/')}
本轮目标：{config.get('goal', '无')}

编译命令（请按顺序执行）：
{_format_cmds(config.get('build_commands', []))}

部署命令（请按顺序执行）：
{_format_cmds(config.get('deploy_commands', []))}

测试命令（请按顺序执行）：
{_format_cmds(config.get('test_commands', []))}

【前情提要】
当前是第 {next_round} 轮。
历史记录如下：
{history_text}

【你的工作流（严格遵守）】
1. 分析前情提要，根据本轮目标，修改代码。
2. 执行【编译命令】。若失败，尝试定位并修复代码重试（建议不超过3次）。
3. 执行【部署命令】。
4. 执行【测试命令】。
5. 无论测试成功还是失败，**立刻停止工作**。绝不允许自行开启下一轮或进入死循环！

【本轮输出要求（极其重要）】
工作停止后，你必须将本轮的执行结果，严格按照以下 JSON 格式，**直接保存到文件** `{history_json_target}` 中（请直接将内容写入文件，不要只输出在对话框里）：

```json
{{
  "round": {next_round},
  "status": "SUCCEEDED或FAILED",
  "bugs_found": "遇到了什么问题，简要描述",
  "fixes_applied": "你是怎么解决的",
  "commits": "提交记录（如果有）",
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

    def _extract_round_num(self, filename: str) -> int:
        match = re.search(r'round_(\d+)\.(json|pending)', filename)
        return int(match.group(1)) if match else 99999

    def _write_json(self, path: Path, obj: Any) -> None:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding='utf-8'))
