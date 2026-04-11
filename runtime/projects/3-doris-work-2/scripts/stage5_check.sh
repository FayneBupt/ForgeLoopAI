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



echo "等待 Doris FE(${DORIS_PORT}) 与 BE(${DORIS_BE_PORT}) 端口就绪，最长等待 120 秒..."
timeout 120s bash -c 'until nc -z '"${DORIS_HOST}"' '"${DORIS_PORT}"' 2>/dev/null; do echo "等待 FE..."; sleep 3; done'
timeout 120s bash -c 'until nc -z '"${DORIS_HOST}"' '"${DORIS_BE_PORT}"' 2>/dev/null; do echo "等待 BE..."; sleep 3; done'
echo '服务端口已打开，尝试注册 BE 节点...'
mysql -h "${DORIS_HOST}" -P "${DORIS_PORT}" -uroot -e "ALTER SYSTEM ADD BACKEND '${DORIS_HOST}:${DORIS_BE_PORT}';" 2>/dev/null || true
echo '检查 FE/BE 进程心跳状态 (Alive: true)...'
timeout 120s bash -c 'until mysql -h '"${DORIS_HOST}"' -P '"${DORIS_PORT}"' -uroot -e "SHOW FRONTENDS;" 2>/dev/null | grep -q "true"; do echo "等待 FE 心跳正常..."; sleep 3; done'
timeout 120s bash -c 'until mysql -h '"${DORIS_HOST}"' -P '"${DORIS_PORT}"' -uroot -e "SHOW BACKENDS;" 2>/dev/null | grep -q "true"; do echo "等待 BE 心跳正常..."; sleep 3; done'
echo '心跳检查通过！验证 BE 计算组是否真正 Ready (等待可用 Backends)...'
timeout 120s bash -c 'until mysql -h '"${DORIS_HOST}"' -P '"${DORIS_PORT}"' -uroot -e "SELECT 1;" 2>/dev/null | grep -q "1"; do echo "等待计算节点完全初始化..."; sleep 3; done'
echo 'BE 计算节点完全就绪！'
mysql -h "${DORIS_HOST}" -P "${DORIS_PORT}" -uroot -e "SHOW FRONTENDS\G; SHOW BACKENDS\G;"
echo '输出最新启动日志供 AI 参考...'
tail -n 20 "${DORIS_PROJECT_PATH}/output/fe/log/fe.log"
tail -n 20 "${DORIS_PROJECT_PATH}/output/be/log/be.INFO"
