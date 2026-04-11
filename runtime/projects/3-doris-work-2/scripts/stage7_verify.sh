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
total=0

PYTHON_BIN=${PYTHON_BIN:-"python3"}
DORIS_HOST=${DORIS_HOST:-"127.0.0.1"}
DORIS_PORT=${DORIS_PORT:-"9145"}
DORIS_FE_HTTP_PORT=${DORIS_FE_HTTP_PORT:-"8143"}
SQL_DIR="${SCRIPT_DIR}/sql"

MODE="all"
TARGET_CASE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --list)
      MODE="list"
      shift
      ;;
    --case)
      MODE="case"
      TARGET_CASE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [ "$MODE" = "list" ]; then
    echo "========== 核心回归验证集用例列表 =========="
    if [ -d "$SQL_DIR" ]; then
        for sql_file in $(ls "$SQL_DIR"/*.sql 2>/dev/null | sort); do
            case_name=$(basename "$sql_file")
            echo "- $case_name"
        done
    fi
    exit 0
fi

echo "========== 开始执行核心回归验证集 =========="

# 遍历 sql 目录下的所有 .sql 文件，并按字母顺序执行
if [ -d "$SQL_DIR" ]; then
    for sql_file in $(ls "$SQL_DIR"/*.sql 2>/dev/null | sort); do
        case_name=$(basename "$sql_file")
        
        if [ "$MODE" = "case" ] && [ "$case_name" != "$TARGET_CASE" ]; then
            continue
        fi
        
        ((total++))
        echo "----------------------------------------"
        echo "👉 [Case $total: $case_name]"

        first_line=$(head -n 1 "$sql_file")
        if echo "$first_line" | grep -iq "@VERIFY:.*DISABLE\|@VERIFY:.*SKIP"; then
            echo "📝 描述: 发现跳过标志，跳过 $case_name 测试用例"
            echo "⏭️ 结果: SKIPPED"
            continue
        fi

        echo "📝 描述: 执行 $case_name 测试用例"
        start_time=$(date +%s.%N)

        if result=$(unset https_proxy http_proxy HTTP_PROXY HTTPS_PROXY PYTHONIOENCODING PYTHONUNBUFFERED && export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 DORIS_FE_HTTP_PORT=$DORIS_FE_HTTP_PORT SEC_TOKEN_STRING=$SEC_TOKEN_STRING; $PYTHON_BIN "${SCRIPT_DIR}/send.py" --host $DORIS_HOST --port $DORIS_PORT --db-psm '' --concurrency 1 --loops 1 --paimon-jni-writer false --sql-file "$sql_file" 2>&1); then
            end_time=$(date +%s.%N)
            cost_time=$(echo "$end_time - $start_time" | bc)
            echo "✅ 结果: SUCCESS"
            printf "⏱️  耗时: %.3fs\n" "$cost_time"
            echo "📊 输出:"
            echo -e "$result"
            ((success++))
        else
            end_time=$(date +%s.%N)
            cost_time=$(echo "$end_time - $start_time" | bc)
            echo "❌ 结果: FAILED"
            printf "⏱️  耗时: %.3fs\n" "$cost_time"
            echo "📉 错误输出:"
            echo -e "$result"
            ((fail++))
        fi
    done
fi

echo "----------------------------------------"
echo "========== 测试结果汇总 =========="
echo "Total: $total, Success: $success, Failed: $fail"
if [ $fail -gt 0 ]; then
    exit 1
fi
