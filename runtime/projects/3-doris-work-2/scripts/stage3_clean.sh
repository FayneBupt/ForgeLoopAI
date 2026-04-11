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



echo '清理 Doris 历史日志和元数据，确保干净启动...'
python3 -c "import shutil, glob, os; targets = ['${DORIS_PROJECT_PATH}/output/fe/log/*', '${DORIS_PROJECT_PATH}/output/be/log/*', '${DORIS_PROJECT_PATH}/output/fe/doris-meta/*', '${DORIS_PROJECT_PATH}/output/be/storage/*']; [shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p) for t in targets for p in glob.glob(t)]" || true
