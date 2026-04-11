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



echo '设置项目专属软连接，便于直接查看日志和数据...'
python3 -c "import os; dirs = ['${DORIS_PROJECT_PATH}/output/fe/log', '${DORIS_PROJECT_PATH}/output/be/log', '${DORIS_PROJECT_PATH}/output/fe/doris-meta', '${DORIS_PROJECT_PATH}/output/be/storage']; [os.makedirs(d, exist_ok=True) for d in dirs]" || true
ln -sfn "${DORIS_PROJECT_PATH}/output/fe/log" "${CONFIG_DIR}/fe-log"
ln -sfn "${DORIS_PROJECT_PATH}/output/be/log" "${CONFIG_DIR}/be-log"
ln -sfn "${DORIS_PROJECT_PATH}/output/fe/doris-meta" "${CONFIG_DIR}/fe-meta"
ln -sfn "${DORIS_PROJECT_PATH}/output/be/storage" "${CONFIG_DIR}/be-storage"
echo '强制移除 start_fe.sh 的内置 Consul 自动发现逻辑，确保单机启动...'
python3 -c "import os; path='${DORIS_PROJECT_PATH}/output/fe/bin/start_fe.sh'; content=open(path).read().replace('        append_helper', '        #append_helper'); open(path,'w').write(content)" || true
echo '覆盖 FE/BE 配置到 Doris output/conf，确保 JDK17 参数生效...'
cp "${CONFIG_DIR}/fe.conf" "${DORIS_PROJECT_PATH}/output/fe/conf/fe.conf"
cp "${CONFIG_DIR}/be.conf" "${DORIS_PROJECT_PATH}/output/be/conf/be.conf"
echo '启动 Doris FE...'
cd "${DORIS_PROJECT_PATH}/output/fe" && doas -p dp.presto.staging_worker env DORIS_CONF_DIR="${CONFIG_DIR}" JAVA_HOME="${JDK17_HOME}" PATH="${JDK17_HOME}/bin:$PATH" http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= bash bin/start_fe.sh --daemon
echo '启动 Doris BE...'
cd "${DORIS_PROJECT_PATH}/output/be" && doas -p dp.presto.staging_worker env DORIS_CONF_DIR="${CONFIG_DIR}" JAVA_HOME="${JDK17_HOME}" PATH="${JDK17_HOME}/bin:$PATH" http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= bash bin/start_be.sh --daemon
