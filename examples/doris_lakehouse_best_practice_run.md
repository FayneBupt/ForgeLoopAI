# Doris Lakehouse 自动化测试生命周期日志 (最佳实践范例)

> 这是一个脱敏后的 `forgeloop run <project> all-no-build` 执行日志样例。
> 通过本日志可以清晰地看到：AI Agent 在执行配置好的 `config.json` 时，是如何通过**健壮的 Bash 探活重试**机制，从环境销毁、部署、到校验完全 Ready，最终完成核心 Bug 复现的。
> 在本样例中，`verify` 阶段成功暴露出我们要让 AI 修复的 Bug（`Invalid: cannot found latest schema in branch main`）。

```text
$ forgeloop run fix-doris-bug-template all-no-build

=======================================================
 开始执行完整生命周期测试 | Project: [fix-doris-bug-template]
 阶段流转: stop -> clean -> deploy -> check -> test -> verify
=======================================================

========== 开始测试执行 fix-doris-bug-template 的 [stop] 阶段 ==========

>>> [stop] 第 1 步: cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker-compose down || true
[+] Running 5/5
 ⠿ Container paimon-flink-taskmanager  Removed
 ⠿ Container paimon-hive-metastore     Removed
 ⠿ Container paimon-datanode           Removed
 ⠿ Container paimon-flink-jobmanager   Removed
 ⠿ Container paimon-namenode           Removed

>>> [stop] 第 2 步: cd /path/to/Doris-Dev-Runner && ./stop_doris.sh /path/to/doris_source_code/output || true
=========================================
 Stopping Doris (Paimon Test Env)
=========================================
[1] Stopping Frontend (FE)...
Waiting for fe process with PID 504347 to terminate
stop java and remove PID file
[2] Stopping Backend (BE)...
Waiting for be process with PID 505753 to terminate
stop doris_be and remove PID file
=========================================
Doris services stopped.
=========================================

>>> [stop] 第 3 步: timeout 60s bash -c 'while ps -ef | grep "[d]oris_" | grep <YOUR_USERNAME> >/dev/null; do echo "等待 Doris 进程完全退出..."; sleep 2; done' || true
等待 Doris 进程完全退出...
等待 Doris 进程完全退出...

========== [stop] 阶段执行成功！ ==========

========== 开始测试执行 fix-doris-bug-template 的 [clean] 阶段 ==========

>>> [clean] 第 1 步: echo '清理 Doris 历史日志和元数据，确保干净启动...'
清理 Doris 历史日志和元数据，确保干净启动...

>>> [clean] 第 2 步: rm -rf /path/to/Doris-Dev-Runner/log/fe/*
>>> [clean] 第 3 步: rm -rf /path/to/Doris-Dev-Runner/log/be/*
>>> [clean] 第 4 步: rm -rf /path/to/doris_source_code/output/fe/doris-meta/*
>>> [clean] 第 5 步: rm -rf /path/to/doris_source_code/output/be/storage/*

========== [clean] 阶段执行成功！ ==========

========== 开始测试执行 fix-doris-bug-template 的 [deploy] 阶段 ==========

>>> [deploy] 第 1 步: cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker-compose up -d
[+] Running 5/5
 ⠿ Container paimon-namenode           Started
 ⠿ Container paimon-flink-jobmanager   Started
 ⠿ Container paimon-flink-taskmanager  Started
 ⠿ Container paimon-hive-metastore     Started
 ⠿ Container paimon-datanode           Started

>>> [deploy] 第 2 步: echo '等待 Hive Metastore (9083) 启动...'
等待 Hive Metastore (9083) 启动...

>>> [deploy] 第 3 步: timeout 120s bash -c 'until sudo docker exec paimon-hive-metastore bash -c "</dev/tcp/127.0.0.1/9083" 2>/dev/null; do sleep 3; done'
... (隐式静默重试中) ...

>>> [deploy] 第 4 步: cd /path/to/Lakehouse-Sandbox-Cluster && sudo docker cp init.sql paimon-flink-jobmanager:/tmp/init.sql && sudo docker exec paimon-flink-jobmanager ./bin/sql-client.sh -f /tmp/init.sql
Successfully copied 2.56kB to paimon-flink-jobmanager:/tmp/init.sql
[INFO] Executing SQL from file.
Flink SQL> CREATE CATALOG paimon_catalog WITH (...)
[INFO] Execute statement succeed.
Flink SQL> CREATE TABLE doris_insert_test (...)
[INFO] Execute statement succeed.
Flink SQL> INSERT INTO doris_insert_test VALUES (1, 'Doris', '2024-05-01'), (2, 'Paimon', '2024-05-01'), (3, 'Flink', '2024-05-02')
[INFO] Submitting SQL update statement to the cluster...
Job ID: baf7a33c93ac4fabfa56d4a5459eb279
Shutting down the session... done.

>>> [deploy] 第 5 步: grep -q 'paimon-namenode' /etc/hosts || echo '127.0.0.1 paimon-namenode paimon-datanode paimon-hive-metastore' | sudo tee -a /etc/hosts

>>> [deploy] 第 6 步: cd /path/to/Doris-Dev-Runner && ./start_doris.sh /path/to/doris_source_code/output
=========================================
 Starting Doris (Paimon Test Env)
=========================================
[0] Using JDK 17
[1] Injecting custom configurations for cluster 'paimon'...
[2] Starting Frontend (FE)...
[3] Starting Backend (BE)...
Doris started successfully in background.

========== [deploy] 阶段执行成功！ ==========

========== 开始测试执行 fix-doris-bug-template 的 [check] 阶段 ==========

>>> [check] 第 1 步: echo '等待 Doris FE(9040) 与 BE(9060) 端口就绪，最长等待 120 秒...'
等待 Doris FE(9040) 与 BE(9060) 端口就绪，最长等待 120 秒...

>>> [check] 第 2 步: timeout 120s bash -c 'until nc -z 127.0.0.1 9040 2>/dev/null; do echo "等待 FE..."; sleep 3; done'
等待 FE...

>>> [check] 第 3 步: timeout 120s bash -c 'until nc -z 127.0.0.1 9060 2>/dev/null; do echo "等待 BE..."; sleep 3; done'
等待 BE...
等待 BE...

>>> [check] 第 4 步: echo '服务端口已打开，尝试注册 BE 节点...'
服务端口已打开，尝试注册 BE 节点...

>>> [check] 第 5 步: mysql -h 127.0.0.1 -P 9040 -uroot -e "ALTER SYSTEM ADD BACKEND '127.0.0.1:9060';" 2>/dev/null || true

>>> [check] 第 6 步: echo '检查 FE/BE 进程心跳状态 (Alive: true)...'
检查 FE/BE 进程心跳状态 (Alive: true)...

>>> [check] 第 7 步: timeout 120s bash -c 'until mysql -h 127.0.0.1 -P 9040 -uroot -e "SHOW FRONTENDS;" 2>/dev/null | grep -q "true"; do echo "等待 FE 心跳正常..."; sleep 3; done'

>>> [check] 第 8 步: timeout 120s bash -c 'until mysql -h 127.0.0.1 -P 9040 -uroot -e "SHOW BACKENDS;" 2>/dev/null | grep -q "true"; do echo "等待 BE 心跳正常..."; sleep 3; done'
等待 BE 心跳正常...
等待 BE 心跳正常...

>>> [check] 第 9 步: echo '心跳检查通过！验证 BE 计算组是否真正 Ready (等待可用 Backends)...'
心跳检查通过！验证 BE 计算组是否真正 Ready (等待可用 Backends)...

>>> [check] 第 10 步: timeout 120s bash -c 'until mysql -h 127.0.0.1 -P 9040 -uroot -e "SELECT 1;" 2>/dev/null | grep -q "1"; do echo "等待计算节点完全初始化..."; sleep 3; done'
等待计算节点完全初始化...
等待计算节点完全初始化...
等待计算节点完全初始化...

>>> [check] 第 11 步: echo 'BE 计算节点完全就绪！'
BE 计算节点完全就绪！

>>> [check] 第 12 步: mysql -h 127.0.0.1 -P 9040 -uroot -e "SHOW FRONTENDS\G; SHOW BACKENDS\G;"
... (省略具体心跳/存储详情日志) ...
              Alive: true
...

>>> [check] 第 13 步: echo '输出最新启动日志供 AI 参考...'
输出最新启动日志供 AI 参考...

>>> [check] 第 14 步: tail -n 20 /path/to/Doris-Dev-Runner/log/fe/fe.log
...
2026-04-04 18:32:09,360 INFO [ReportHandler.tabletReport():588] backend[1775295797367] reports 22 tablet(s).
...

>>> [check] 第 15 步: tail -n 20 /path/to/Doris-Dev-Runner/log/be/be.INFO
...
I20260404 18:32:00.591837 569590 thrift_server.cpp:423] ThriftServer 'heartbeat' started on port: 9060
...

========== [check] 阶段执行成功！ ==========

========== 开始测试执行 fix-doris-bug-template 的 [test] 阶段 ==========

>>> [test] 第 1 步: echo '==== 开始执行环境测试 (Test) ===='
==== 开始执行环境测试 (Test) ====

>>> [test] 第 2 步: echo '[Test 1/3] 重建 Catalog (paimon_hive_catalog)...'
[Test 1/3] 重建 Catalog (paimon_hive_catalog)...

>>> [test] 第 3 步: mysql -h 127.0.0.1 -P 9040 -uroot -e "DROP CATALOG IF EXISTS paimon_hive_catalog; CREATE CATALOG paimon_hive_catalog ..."

>>> [test] 第 4 步: echo '[Test 2/3] 验证表结构是否可查...'
[Test 2/3] 验证表结构是否可查...

>>> [test] 第 5 步: mysql -h 127.0.0.1 -P 9040 -uroot -e "SWITCH paimon_hive_catalog; USE doris_paimon_db; SHOW TABLES;"
+---------------------------+
| Tables_in_doris_paimon_db |
+---------------------------+
| doris_insert_test         |
+---------------------------+

>>> [test] 第 6 步: echo '[Test 3/3] 验证 Flink 初始预置数据是否能正常读取...'
[Test 3/3] 验证 Flink 初始预置数据是否能正常读取...

>>> [test] 第 7 步: mysql -h 127.0.0.1 -P 9040 -uroot -e "SWITCH paimon_hive_catalog; USE doris_paimon_db; SELECT * FROM doris_insert_test ORDER BY id LIMIT 10;"
+------+--------+------------+
| id   | name   | dt         |
+------+--------+------------+
|    1 | Doris  | 2024-05-01 |
|    2 | Paimon | 2024-05-01 |
|    3 | Flink  | 2024-05-02 |
+------+--------+------------+

>>> [test] 第 8 步: echo '==== 环境测试完毕，具备回归验证条件 ===='
==== 环境测试完毕，具备回归验证条件 ====

========== [test] 阶段执行成功！ ==========

========== 开始测试执行 fix-doris-bug-template 的 [verify] 阶段 ==========

>>> [verify] 第 1 步: echo '==== 开始核心回归验证 (Verify) ===='
==== 开始核心回归验证 (Verify) ====

>>> [verify] 第 2 步: echo '[Verify 1/1] 执行 INSERT INTO 操作并查询验证结果...'
[Verify 1/1] 执行 INSERT INTO 操作并查询验证结果...

>>> [verify] 第 3 步: mysql -h 127.0.0.1 -P 9040 -uroot -e "SWITCH paimon_hive_catalog; USE doris_paimon_db; INSERT INTO doris_insert_test VALUES (1001,'from_doris_insert_case','2026-04-03'); SELECT * FROM doris_insert_test ORDER BY id DESC LIMIT 20;"
ERROR 1105 (HY000) at line 1: errCode = 2, detailMessage = (127.0.0.1)[INTERNAL_ERROR]failed to create paimon file store write: Invalid: cannot found latest schema in branch main

[Error] 命令执行失败，退出码: 1

[Fatal] 完整生命周期测试在 [verify] 阶段失败退出！
```