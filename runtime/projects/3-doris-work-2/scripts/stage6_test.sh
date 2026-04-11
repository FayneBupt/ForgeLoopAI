#!/bin/bash
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



success=0
fail=0

echo "========== 开始执行环境测试集 (Test) =========="

echo "----------------------------------------"
echo "👉 [Test 1: 创建场内 Catalog (paimon_1)]"
echo "📝 描述: 连接 bytedance_hive 创建场内 Paimon Catalog"
if result=$(mysql -h "${DORIS_HOST}" -P "${DORIS_PORT}" -uroot -e "DROP CATALOG IF EXISTS paimon_1; CREATE CATALOG paimon_1 PROPERTIES ( 'use_meta_cache' = 'true', 'type' = 'paimon', 'region' = 'CN', 'paimon.catalog.type' = 'hms', 'hive.metastore.type' = 'bytedance_hive', 'default-format' = 'parquet' );" 2>&1); then
    echo "✅ 结果: SUCCESS"
    echo "📊 输出:"
    echo "$result"
    ((success++))
else
    echo "❌ 结果: FAILED"
    echo "📉 错误输出:"
    echo "$result"
    ((fail++))
fi

echo "----------------------------------------"
echo "👉 [Test 2: 创建场内 Catalog (default_hive_catalog)]"
echo "📝 描述: 连接 bytedance_hive 创建场内 hive Catalog"
if result=$(mysql -h "${DORIS_HOST}" -P "${DORIS_PORT}" -uroot -e "DROP CATALOG IF EXISTS default_hive_catalog; CREATE CATALOG default_hive_catalog PROPERTIES ( 'staging_dir' = 'xxx', 'type' = 'hms', 'region' = 'CN', 'hive.metastore.type' = 'bytedance_hive', 'default-format' = 'parquet' );" 2>&1); then
    echo "✅ 结果: SUCCESS"
    echo "📊 输出:"
    echo "$result"
    ((success++))
else
    echo "❌ 结果: FAILED"
    echo "📉 错误输出:"
    echo "$result"
    ((fail++))
fi

echo "----------------------------------------"
echo "========== 环境测试结果汇总 =========="
echo "Total: 2, Success: $success, Failed: $fail"
if [ $fail -gt 0 ]; then
    exit 1
fi
