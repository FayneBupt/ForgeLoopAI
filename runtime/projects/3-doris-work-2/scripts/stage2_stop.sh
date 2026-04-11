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



PIDS=$(ps -ef | grep -E "[d]oris_be|[D]orisFE" | grep "${DORIS_USERNAME}" | grep "${DORIS_PROJECT_PATH}/output" | awk '{print $2}')
if [ -n "$PIDS" ]; then echo "$PIDS" | xargs -r kill || true; fi
timeout 20s bash -c 'while ps -ef | grep -E "[d]oris_be|[D]orisFE" | grep "'"${DORIS_USERNAME}"'" | grep "'"${DORIS_PROJECT_PATH}/output"'" >/dev/null; do echo "等待 Doris 进程优雅退出..."; sleep 2; done' || true
REMAINING=$(ps -ef | grep -E "[d]oris_be|[D]orisFE" | grep "${DORIS_USERNAME}" | grep "${DORIS_PROJECT_PATH}/output" | awk '{print $2}')
if [ -n "$REMAINING" ]; then echo "$REMAINING" | xargs -r kill -9 || true; fi
timeout 10s bash -c 'while ps -ef | grep -E "[d]oris_be|[D]orisFE" | grep "'"${DORIS_USERNAME}"'" | grep "'"${DORIS_PROJECT_PATH}/output"'" >/dev/null; do echo "等待 Doris 进程强杀后退出..."; sleep 1; done' || true
