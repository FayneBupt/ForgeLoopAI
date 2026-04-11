#!/usr/bin/env python
# -*- coding:utf-8 -*-
import argparse
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import byteddoris
from byteddoris.connection import BytedDorisConnection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
PRINT_LOCK = threading.Lock()

def _is_explain_sql(sql: str) -> bool:
    s = (sql or "").lstrip().lower()
    return s.startswith("explain")

def _print_result(sql: str, loop_index: int, sql_index: int, sql_total: int, cursor, rows) -> None:
    # ANSI Color codes
    CYAN = "\033[1;36m"
    YELLOW = "\033[1;33m"
    GREEN = "\033[1;32m"
    RESET = "\033[0m"
    
    with PRINT_LOCK:
        header_type = "EXPLAIN" if _is_explain_sql(sql) else "RESULT"
        header = f"[{header_type}] loop {loop_index} sql {sql_index}/{sql_total}"
        
        # Print SQL with Cyan color
        if sql and sql.strip():
            print(f"\n{CYAN}========== SQL EXECUTED =========={RESET}")
            print(f"{CYAN}{sql.strip()}{RESET}")
            print(f"{CYAN}=================================={RESET}")
            
        print("\n" + "=" * len(header))
        print(header)
        print("=" * len(header))
        
        # Print Result with Yellow color
        print(YELLOW, end="")
        if cursor.description:
            col_names = [c[0] for c in cursor.description]
            print("\t".join(col_names))
        for row in rows or []:
            if isinstance(row, (tuple, list)):
                print("\t".join("NULL" if v is None else str(v) for v in row))
            else:
                print("NULL" if row is None else str(row))
        print(RESET, end="")
        sys.stdout.flush()

class PatchedBytedDorisConnection(BytedDorisConnection):
    """
    Patched connection class to fix AttributeError in byteddoris library.
    """
    def _connect(self, **kwargs):
        try:
            if self.db_psm:
                return self._connect_by_consul(**kwargs)
            if self.use_gdpr_auth:
                if 'user' in kwargs:
                    self._user = kwargs['user']
                host = kwargs.get('host')
                self._gen_gdpr_user(host)
                kwargs['user'] = self._user
                if hasattr(self, '_host'):
                    kwargs['host'] = self._host
                if hasattr(self, '_port'):
                    kwargs['port'] = self._port
            # Skip BytedDorisConnection._connect and go straight to CMySQLConnection.connect
            return super(BytedDorisConnection, self).connect(**kwargs)
        except Exception as ex:
            # Raise the original exception
            raise ex

    def _gen_gdpr_user(self, host):
        import os
        import requests
        import byteddps
        from byteddoris.exception import GdprError
        
        token = byteddps.get_token()
        
        # Override http_port via DORIS_FE_HTTP_PORT, fallback to 8030
        http_port = os.environ.get("DORIS_FE_HTTP_PORT", "8030")
        
        # Auto-detect IPv4/IPv6
        is_ipv6 = ":" in host
        
        if is_ipv6:
            url = f"http://[{host}]:{http_port}/api/account/gen?token={token}"
        else:
            url = f"http://{host}:{http_port}/api/account/gen?token={token}"

        r = requests.post(url)
        if r.status_code != requests.codes.ok:
            raise GdprError(f"[byteddoris] post {url} failed, ex: {r.raise_for_status()}")
        if int(r.json()['errno']) != 0:
            raise GdprError(f"[byteddoris] gen gdpr account failed, url: {url}, result: {r.json()} ")
            
        # update info in CMySQLConnection
        if r.json().get('fe_host_ipv6') and not str(r.json()['fe_host_ipv6']).isspace():
            self._host = r.json()['fe_host_ipv6']
        else:
            self._host = r.json()['fe_host']

        self._port = int(r.json()['fe_port'])
        self._user = r.json()['username'] + ":" + self._user

def connect(*args, **kwargs):
    """Factory function to create a patched connection."""
    return PatchedBytedDorisConnection(**kwargs)

def get_connection(host, port, user, password, db_psm):
    """
    Establishes a connection to Doris.
    """
    common_args = {
        "charset": "utf8mb4",
        "connect_timeout": 5,
        "read_timeout": 5,
        "write_timeout": 5,
    }

    if db_psm:
        # Connect via PSM
        return connect(
            user=user,
            password=password,
            db_psm=db_psm,
            use_gdpr_auth=True,
            **common_args
        )
    else:
        # Connect via Host/IP
        return connect(
            host=host,
            port=port,
            user=user,
            password=password,
            use_gdpr_auth=True,
            **common_args
        )

def parse_args():
    parser = argparse.ArgumentParser(description="Doris Connection Script")
    parser.add_argument("--host", default="None")
    parser.add_argument("--port", type=int, default=9030)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default=os.environ.get("DORIS_PASSWORD", ""))
    parser.add_argument("--db-psm", default="olap.doris.doris_sre_test_ha_emr_lf_mysql.service.lf")

    sql_group = parser.add_mutually_exclusive_group()
    sql_group.add_argument("--sql", default=None)
    sql_group.add_argument("--sql-file", default=None)
    sql_group.add_argument("--sql-list-file", default=None)

    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--loops", type=int, default=1)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--query-timeout", type=int, default=5)
    parser.add_argument("--parallel-fragment-exec-instance-num", type=int, default=3)
    parser.add_argument("--continue-on-error", action="store_true", default=False)
    parser.add_argument("--paimon-jni-writer", choices=["true", "false"], default="false")
    parser.add_argument("--paimon-jni-compact", choices=["true", "false"], default="true")
    parser.add_argument("--enable-paimon-jni-writer-fallback", action="store_true", default=False)

    parser.add_argument("--fallback-psm", default="inf.compute.doris_test_mysql.service.lf")
    parser.add_argument("--fallback-user", default="root")
    parser.add_argument("--fallback-password", default="")
    return parser.parse_args()

def split_sql_statements(text):
    parts = []
    buf = []
    in_single = False
    in_double = False
    escape = False
    
    # We will keep track of comments leading up to a statement
    current_comments = []
    
    # Simple line-by-line pre-processing to extract comments and associate them
    lines = text.split('\n')
    processed_text = ""
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("--"):
            current_comments.append(line)
        else:
            if current_comments and line_stripped:
                # We have some comments and now a non-comment line
                processed_text += "\n".join(current_comments) + "\n"
                current_comments = []
            elif current_comments and not line_stripped:
                # Still collecting or trailing comments, keep them
                processed_text += "\n".join(current_comments) + "\n"
                current_comments = []
            processed_text += line + "\n"
            
    if current_comments:
        processed_text += "\n".join(current_comments) + "\n"

    # Now do the standard split on the processed text
    for ch in processed_text:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\":
            buf.append(ch)
            escape = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            continue
        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts

def parse_assertions(sql_stmt):
    """
    Parse @EXPECT assertions from SQL comments.
    Returns a dict with assertion configurations.
    """
    assertions = {}
    lines = sql_stmt.split('\n')
    
    # Extract RESULT rows
    result_rows = []
    collecting_result = False
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped.startswith("--"):
            collecting_result = False
            continue
            
        comment = line_stripped[2:].strip()
        
        if comment.startswith("@EXPECT:"):
            collecting_result = False
            parts = comment.split(":", 1)[1].strip().split(" ", 1)
            cmd = parts[0].upper()
            val = parts[1].strip() if len(parts) > 1 else ""
            
            if cmd == "EXCEPTION":
                assertions["EXCEPTION"] = val
            elif cmd == "ROW_COUNT":
                try:
                    assertions["ROW_COUNT"] = int(val)
                except ValueError:
                    pass
            elif cmd == "NONE" or cmd == "EMPTY":
                assertions["ROW_COUNT"] = 0
            elif cmd == "RESULT":
                assertions["RESULT"] = []
                collecting_result = True
        elif collecting_result:
            # Assume it's a result row if we are in collecting_result mode
            # Support comma-separated values in comments
            row_data = [x.strip() for x in comment.split(',')]
            assertions["RESULT"].append(row_data)
            
    return assertions

def assert_sql_result(sql, assertions, cursor, result_rows):
    if not assertions:
        return
        
    CYAN = "\033[1;36m"
    RED = "\033[1;31m"
    GREEN = "\033[1;32m"
    RESET = "\033[0m"
    
    print(f"\n{CYAN}========== ASSERTION CHECK =========={RESET}")
    
    if "ROW_COUNT" in assertions:
        expected = assertions["ROW_COUNT"]
        actual = len(result_rows)
        if expected != actual:
            msg = f"Assertion Failed: ROW_COUNT mismatch. Expected: {expected}, Actual: {actual}"
            print(f"{RED}❌ {msg}{RESET}")
            raise AssertionError(msg)
        else:
            print(f"{GREEN}✅ ROW_COUNT ({actual}) matched.{RESET}")
            
    if "RESULT" in assertions:
        expected_rows = assertions["RESULT"]
        
        # Check row count first for RESULT
        if len(expected_rows) != len(result_rows):
            msg = f"Assertion Failed: RESULT row count mismatch. Expected: {len(expected_rows)}, Actual: {len(result_rows)}"
            print(f"{RED}❌ {msg}{RESET}")
            raise AssertionError(msg)
            
        # Check cell by cell
        for r_idx, (exp_row, act_row) in enumerate(zip(expected_rows, result_rows)):
            act_row_list = [str(x) if x is not None else "NULL" for x in act_row]
            if len(exp_row) != len(act_row_list):
                msg = f"Assertion Failed: Column count mismatch at row {r_idx}. Expected: {len(exp_row)}, Actual: {len(act_row_list)}"
                print(f"{RED}❌ {msg}{RESET}")
                raise AssertionError(msg)
                
            for c_idx, (exp_val, act_val) in enumerate(zip(exp_row, act_row_list)):
                if exp_val != act_val:
                    msg = f"Assertion Failed: Data mismatch at row {r_idx}, col {c_idx}. Expected: '{exp_val}', Actual: '{act_val}'"
                    print(f"{RED}❌ {msg}{RESET}")
                    raise AssertionError(msg)
                    
        print(f"{GREEN}✅ RESULT ({len(expected_rows)} rows) exactly matched.{RESET}")

def resolve_sql_list(args):
    if args.sql is not None:
        return [args.sql]
    if args.sql_file is not None:
        with open(args.sql_file, "r", encoding="utf-8") as f:
            content = f.read()
        stmts = split_sql_statements(content)
        return stmts if stmts else [content]
    if args.sql_list_file is not None:
        with open(args.sql_list_file, "r", encoding="utf-8") as f:
            content = f.read()
        return split_sql_statements(content)

    # Fallback to a simple health check if no SQL is provided
    return ["SELECT 1"]

def apply_session_settings(cursor, args, writer_value=None):
    cursor.execute(f"set query_timeout = {args.query_timeout}")
    cursor.execute("set enable_fallback_to_original_planner=false")
    cursor.execute("set nereids_timeout_second=100")
    cursor.execute("set insert_timeout=100000")
    cursor.execute("set enable_profile=true")
    cursor.execute("set force_send_profile=true")
    cursor.execute("set enable_pipeline_x_engine=true")
    cursor.execute("set parallel_pipeline_task_num=64")
    cursor.execute("set parallel_fragment_exec_instance_num =8")
    cursor.execute("set file_split_size=134217728")
    cursor.execute("set batch_size=4064")
    current_writer = args.paimon_jni_writer if writer_value is None else writer_value
    cursor.execute(f"set enable_paimon_jni_writer={current_writer}")
    cursor.execute(f"set enable_paimon_jni_compact={args.paimon_jni_compact}")
    cursor.execute("set enable_paimon_distributed_bucket_shuffle=true")
    cursor.execute("set paimon_writer_queue_size=50")
    cursor.execute("set paimon_target_file_size=268435456")
    cursor.execute("set paimon_write_buffer_size=268435456")
    cursor.execute("set enable_paimon_jni_spill=true")
    cursor.execute("set paimon_spill_compression=zstd")
    cursor.execute("set paimon_spill_max_disk_size=10737418240")
    cursor.execute("set paimon_global_memory_pool_size=1073741824")
    cursor.execute("set enable_paimon_adaptive_buffer_size = false")

def execute_sql_with_retry(args, sql, loop_index, sql_index, sql_total):
    conn = None
    cursor = None
    try_times = args.retries
    while try_times > 0:
        try:
            logger.info(
                f"Loop {loop_index}/{args.loops} executing sql {sql_index}/{sql_total}"
            )
            conn = get_connection(args.host, args.port, args.user, args.password, args.db_psm)
            cursor = conn.cursor()

            apply_session_settings(cursor, args)
            
            assertions = parse_assertions(sql)
            try:
                cursor.execute(sql)
                result = cursor.fetchall()
                if result is None:
                    result = []
                logger.info(
                    f"Loop {loop_index}/{args.loops} sql {sql_index}/{sql_total} result_rows={len(result)}"
                )
                # 无论是否有 cursor.description（如 INSERT），都打印 SQL 和可能的结果
                _print_result(sql, loop_index, sql_index, sql_total, cursor, result[:50])
                
                # Check assertion for success flow
                assert_sql_result(sql, assertions, cursor, result)
                
            except AssertionError as ae:
                logger.error(f"Loop {loop_index}/{args.loops} sql {sql_index}/{sql_total} ASSERTION FAILED: {ae}")
                raise ae
            except Exception as e:
                # INSERT / UPDATE 等非查询语句通常会抛出没有结果集的异常
                logger.info(f"No result set to fetch or fetch error: {e}")
                # 就算没有结果，也要把执行了什么 SQL 用高亮打印出来
                _print_result(sql, loop_index, sql_index, sql_total, cursor, [])
                
                # Check if it's an expected exception
                err_msg = str(e)
                if "EXCEPTION" in assertions:
                    exp_err = assertions["EXCEPTION"]
                    if exp_err in err_msg:
                        GREEN = "\033[1;32m"
                        RESET = "\033[0m"
                        print(f"\n{GREEN}✅ ASSERTION PASS: Exception matched '{exp_err}'{RESET}")
                        logger.info(f"Loop {loop_index}/{args.loops} done sql {sql_index}/{sql_total} (Expected Exception Captured)")
                        return
                    else:
                        RED = "\033[1;31m"
                        RESET = "\033[0m"
                        print(f"\n{RED}❌ ASSERTION FAILED: Expected exception containing '{exp_err}', but got: {err_msg}{RESET}")
                        raise AssertionError(f"Expected exception '{exp_err}' not matched in '{err_msg}'")

            logger.info(f"Loop {loop_index}/{args.loops} done sql {sql_index}/{sql_total}")
            return

        except byteddoris.Error as e:
            logger.error(f"Doris Error: {e}")
            if (
                args.enable_paimon_jni_writer_fallback
                and args.paimon_jni_writer == "false"
                and "paimon-cpp parquet file format factory is not registered" in str(e)
            ):
                logger.warning("Detected paimon-cpp parquet factory missing. Retry once with enable_paimon_jni_writer=true fallback.")
                try:
                    conn = get_connection(args.host, args.port, args.user, args.password, args.db_psm)
                    cursor = conn.cursor()
                    apply_session_settings(cursor, args, writer_value="true")
                    cursor.execute(sql)
                    try:
                        result = cursor.fetchall()
                        if result is None:
                            result = []
                        logger.info(
                            f"Loop {loop_index}/{args.loops} sql {sql_index}/{sql_total} fallback result_rows={len(result)}"
                        )
                        if cursor.description is not None:
                            _print_result(sql, loop_index, sql_index, sql_total, cursor, result[:50])
                    except Exception as fetch_error:
                        logger.info(f"No result set to fetch or fetch error: {fetch_error}")
                    logger.info(
                        f"Loop {loop_index}/{args.loops} done sql {sql_index}/{sql_total} with fallback writer=true"
                    )
                    return
                except Exception as fallback_error:
                    logger.error(f"Fallback writer=true failed: {fallback_error}")
            try_times -= 1

            if try_times == 0:
                logger.error("Max retries reached. Exiting.")
                raise e

            if e.args and e.args[0] in (2013, 2006):
                logger.warning("Connection lost. Attempting fallback connection...")
                try:
                    conn = get_connection(
                        None,
                        None,
                        args.fallback_user,
                        args.fallback_password,
                        db_psm=args.fallback_psm,
                    )
                    cursor = conn.cursor()
                    cursor.execute(f"set query_timeout = {args.query_timeout}")
                except Exception as fallback_error:
                    logger.error(f"Fallback connection failed: {fallback_error}")
                    raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

def run_one_loop(args, loop_index, sql_list):
    sql_total = len(sql_list)
    loop_start = time.perf_counter()
    logger.info(
        f"Loop {loop_index}/{args.loops} start concurrency={args.concurrency} sql_total={sql_total}"
    )

    completed = 0
    completed_lock = threading.Lock()

    def task(sql, sql_index):
        try:
            execute_sql_with_retry(args, sql, loop_index, sql_index, sql_total)
        except Exception as e:
            logger.error(
                f"Loop {loop_index}/{args.loops} sql {sql_index}/{sql_total} failed: {e}"
            )
            if not args.continue_on_error:
                raise
        finally:
            nonlocal completed
            with completed_lock:
                completed += 1
                logger.info(
                    f"Loop {loop_index}/{args.loops} progress {completed}/{sql_total} concurrency={args.concurrency}"
                )

    if args.concurrency == 1:
        for idx, sql in enumerate(sql_list, start=1):
            task(sql, idx)
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [
                executor.submit(task, sql, idx)
                for idx, sql in enumerate(sql_list, start=1)
            ]
            first_error = None
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    if first_error is None:
                        first_error = e
                    if not args.continue_on_error:
                        for f in futures:
                            f.cancel()
                        break
            if first_error is not None and not args.continue_on_error:
                raise first_error

    loop_cost = time.perf_counter() - loop_start
    logger.info(f"Loop {loop_index}/{args.loops} finish cost_s={loop_cost:.3f}")

def main():
    args = parse_args()
    if args.concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if args.loops < 1:
        raise ValueError("loops must be >= 1")
    if args.retries < 1:
        raise ValueError("retries must be >= 1")
    if args.query_timeout < 1:
        raise ValueError("query-timeout must be >= 1")
    if args.parallel_fragment_exec_instance_num < 1:
        raise ValueError("parallel-fragment-exec-instance-num must be >= 1")
    if args.sleep < 0:
        raise ValueError("sleep must be >= 0")

    sql_list = resolve_sql_list(args)
    if not sql_list:
        raise ValueError("sql list is empty")

    overall_start = time.perf_counter()
    logger.info(
        f"Overall start loops={args.loops} concurrency={args.concurrency} sql_total={len(sql_list)}"
    )
    for i in range(1, args.loops + 1):
        run_one_loop(args, i, sql_list)
        if args.sleep > 0 and i < args.loops:
            time.sleep(args.sleep)
    overall_cost = time.perf_counter() - overall_start
    logger.info(f"Overall finish cost_s={overall_cost:.3f}")

if __name__ == "__main__":
    main()
