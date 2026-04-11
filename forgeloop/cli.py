import argparse
import json
import time
import sys
from pathlib import Path

from .project_ops import ProjectWorkspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='forgeloop', description="ForgeLoopAI 极简上下文/Prompt管理器")
    sub = parser.add_subparsers(dest='command', required=True)

    init_cmd = sub.add_parser('init', help='初始化一个新项目配置')
    init_cmd.add_argument('name', help='项目名称')

    rm_cmd = sub.add_parser('rm', help='删除一个项目及其所有历史记录')
    rm_cmd.add_argument('name', help='项目名称')

    mission_cmd = sub.add_parser('mission', help='生成本次战役的终极任务执行清单 (mission.md)，融合前情提要，推动单轮强力闭环')
    mission_cmd.add_argument('name', help='项目名称')

    status_cmd = sub.add_parser('status', help='查看所有项目或单个项目的简要记录（路径、创建时间等）')
    status_cmd.add_argument('name', nargs='?', help='项目名称（可选，不填则列出所有项目）')

    run_cmd = sub.add_parser('run', help='测试执行 config.json 中配置的生命周期阶段，支持单阶段或逗号分隔多阶段（例如 stop,clean）')
    run_cmd.add_argument('name', help='项目名称')
    run_cmd.add_argument('stage', help='要执行的阶段（build/stop/clean/deploy/check/test/verify/all/all-no-build），支持逗号分隔并按输入顺序执行')
    run_cmd.add_argument('--build-target', choices=['all', 'be', 'fe'], default=None, help='编译目标（仅在 build 阶段生效）：all/be/fe')
    run_cmd.add_argument('--list', action='store_true', help='[仅 verify 阶段] 列出所有测试用例')
    run_cmd.add_argument('--case', type=str, help='[仅 verify 阶段] 指定执行某个测试用例 (例如 a1.sql)')

    start_cmd = sub.add_parser('start', help='执行 runtime/projects/tools 下的 Python 脚本，例如 start_with_auth')
    start_cmd.add_argument('script', help='脚本名（可省略 .py）')
    start_cmd.add_argument('script_args', nargs=argparse.REMAINDER, help='透传给脚本的参数，建议用 -- 分隔')

    debug_cmd = sub.add_parser('debug', help='自动采集 FE/BE JNI/BE GDB 堆栈并保存到项目目录的 debug-时间戳 文件夹')
    debug_cmd.add_argument('name', help='项目名称')

    return parser


def main() -> None:
    started = time.perf_counter()
    parser = build_parser()
    args = parser.parse_args()

    # 由于我们希望全局可用，但数据保存在 ForgeLoopAI 源码目录下的 runtime 中
    # 所以我们需要获取这个项目代码的绝对路径，从而推导出 runtime 的固定位置
    code_dir = Path(__file__).resolve().parent.parent
    workspace_root = code_dir / 'runtime'
    local_profile_path = code_dir / 'forgeloop.local.json'
    local_profile = {}
    if local_profile_path.exists():
        local_profile = json.loads(local_profile_path.read_text(encoding='utf-8'))
    workspace = ProjectWorkspace(workspace_root, local_profile=local_profile)

    if args.command == 'init':
        result = workspace.init_project(args.name)
    elif args.command == 'rm':
        result = workspace.rm_project(args.name)
    elif args.command == 'mission':
        result = workspace.generate_mission(args.name)
    elif args.command == 'status':
        result = workspace.project_status(args.name)
    elif args.command == 'run':
        code = workspace.run_stage(args.name, args.stage, build_target=args.build_target, list_cases=args.list, case_name=args.case)
        print(f"\n[Timing] 命令总耗时: {time.perf_counter() - started:.3f}s")
        sys.exit(code)
    elif args.command == 'start':
        code = workspace.run_start(args.script, args.script_args)
        print(f"\n[Timing] 命令总耗时: {time.perf_counter() - started:.3f}s")
        sys.exit(code)
    elif args.command == 'debug':
        result = workspace.debug_project(args.name)
    else:
        raise RuntimeError('unknown command')

    # 格式化输出
    if args.command == 'status' and result.get("status") == "success":
        projects = result.get("projects", [])
        if not projects:
            print("当前没有任何项目。请使用 `forgeloop init <name>` 创建。")
        else:
            for i, p in enumerate(projects, 1):
                print(f"*************************** {i}. row ***************************")
                print(f"       Project: {p['project']}")
                print(f"    Created At: {p['created_at']}")
                print(f"   Config Path: {p['config_path']}")
                print(f"  Mission Path: {p['mission_path']}")
            print(f"{len(projects)} rows in set")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[Timing] 命令总耗时: {time.perf_counter() - started:.3f}s")

if __name__ == '__main__':
    main()
