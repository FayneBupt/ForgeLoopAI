import argparse
import json
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

    run_cmd = sub.add_parser('run', help='测试执行 config.json 中配置的各个生命周期阶段（例如 build/stop/deploy），或者执行 all 跑通全流程')
    run_cmd.add_argument('name', help='项目名称')
    run_cmd.add_argument('stage', choices=['build', 'stop', 'clean', 'deploy', 'check', 'test', 'verify', 'all', 'all-no-build'], help='要测试的生命周期阶段，或者使用 all 按序执行全部，all-no-build 则跳过编译')

    compile_cmd = sub.add_parser('compile', help='[高阶功能] 将 config.json 中的内联命令自动提取为独立的 bash 脚本并更新配置，方便 AI 无错执行')
    compile_cmd.add_argument('name', help='项目名称')

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # 由于我们希望全局可用，但数据保存在 ForgeLoopAI 源码目录下的 runtime 中
    # 所以我们需要获取这个项目代码的绝对路径，从而推导出 runtime 的固定位置
    code_dir = Path(__file__).resolve().parent.parent
    workspace_root = code_dir / 'runtime'
    workspace = ProjectWorkspace(workspace_root)

    if args.command == 'init':
        result = workspace.init_project(args.name)
    elif args.command == 'rm':
        result = workspace.rm_project(args.name)
    elif args.command == 'mission':
        result = workspace.generate_mission(args.name)
    elif args.command == 'status':
        result = workspace.project_status(args.name)
    elif args.command == 'run':
        # run 是直接打印日志到终端，它返回的是执行的状态
        import sys
        code = workspace.run_stage(args.name, args.stage)
        sys.exit(code)
    elif args.command == 'compile':
        result = workspace.compile_scripts(args.name)
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

if __name__ == '__main__':
    main()
