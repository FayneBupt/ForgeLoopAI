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

    push_cmd = sub.add_parser('push', help='生成下一轮的 Prompt，推动开发闭环')
    push_cmd.add_argument('name', help='项目名称')

    status_cmd = sub.add_parser('status', help='查看所有项目或单个项目的进度状态')
    status_cmd.add_argument('name', nargs='?', help='项目名称（可选，不填则列出所有项目）')

    show_cmd = sub.add_parser('show', help='展示指定项目的所有历史轮次详情')
    show_cmd.add_argument('name', help='项目名称')

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
    elif args.command == 'push':
        result = workspace.push_project(args.name)
    elif args.command == 'status':
        result = workspace.project_status(args.name)
    elif args.command == 'show':
        result = workspace.show_project(args.name)
    else:
        raise RuntimeError('unknown command')

    # 格式化输出
    if args.command == 'status' and result.get("status") == "success":
        projects = result.get("projects", [])
        if not projects:
            print("当前没有任何项目。请使用 `forgeloop init <name>` 创建。")
        else:
            def c_len(text: str) -> int:
                """计算包含中文字符的字符串显示宽度"""
                return sum(2 if ord(c) > 127 else 1 for c in str(text))
                
            def pad(text: str, width: int) -> str:
                text = str(text)
                return text + " " * max(0, width - c_len(text))

            print(f"{pad('项目名称', 25)} | {pad('轮次', 6)} | {pad('消耗Tokens', 12)} | {pad('最新状态', 20)}")
            print("-" * 70)
            for p in projects:
                print(f"{pad(p['project'], 25)} | {pad(p['rounds'], 6)} | {pad(p['total_tokens'], 12)} | {p['last_status']}")
    elif args.command == 'show' and result.get("status") == "success":
        history = result.get("history", [])
        if not history:
            print(f"项目 {args.name} 暂无历史轮次记录。")
        else:
            print(f"========== 项目 {args.name} 的历史轮次详情 ==========")
            for h in history:
                print(json.dumps(h, ensure_ascii=False, indent=2))
                print("-" * 50)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
