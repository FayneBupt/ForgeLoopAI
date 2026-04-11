#!/bin/bash
set -e
# 自动加载本地脱敏环境变量与全局鉴权 Token
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CONFIG_DIR="${CONFIG_DIR:-$(dirname "$SCRIPT_DIR")}"
if [ -f "${CONFIG_DIR}/config.local.json" ]; then
    eval "$(python3 -c 'import json,sys; c=json.load(open(sys.argv[1])) if len(sys.argv)>1 else {}; [print(f"export {k}=\"{v}\"") for k,v in c.get("env",{}).items()]' "${CONFIG_DIR}/config.local.json")"
fi

FORGELOOP_ROOT="$(cd "${CONFIG_DIR}/../.." && pwd)"
if [ -f "${FORGELOOP_ROOT}/forgeloop.local.json" ]; then
    eval "$(python3 -c 'import json,sys; c=json.load(open(sys.argv[1])) if len(sys.argv)>1 else {}; t=c.get("SEC_TOKEN_STRING"); print(f"export SEC_TOKEN_STRING=\"{t}\"") if t else ""' "${FORGELOOP_ROOT}/forgeloop.local.json")"
fi



echo "开始执行编译..."
