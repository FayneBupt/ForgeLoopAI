你是 Trae Solo Coder。

请在项目路径执行闭环开发测试：/data01/home/lvliangliang/code/osdoris/doris
项目名：doris-lakehouse
当前轮次：Round 2
最大轮次：5

目标功能：
请填写本次开发/修复目标

验收标准：
- 请填写验收标准1
- 请填写验收标准2

测试用例：
- case_001: 请填写用例描述
  command: 请填写测试命令
  expected: 请填写期望结果

环境准备命令：
- sudo docker compose -f docker-compose.yml up -d

编译命令：
- SKIP_CONTRIB_SUBMODULE_UPDATE=1 bash build.sh --be -j8
- SKIP_CONTRIB_SUBMODULE_UPDATE=1 bash build.sh --fe

部署命令：
- bash deploy.sh

测试命令：
- bash run-regression-test.sh

日志定位命令：
- tail -n 200 /path/to/be.INFO
- tail -n 200 /path/to/fe.log

历史轮次：
- Round 1 | status=ROUND_FAILED | bugs=jni null pointer | fixes=add null check | commits=abc123 | tokens=1800

执行要求：
1. 自动执行编译、部署、测试。
2. 失败时定位日志并修复代码后再次编译部署测试。
3. 当遇到高风险操作时先暂停并等待我确认。
4. 每轮结束输出固定格式：
   - round_status:
   - bugs_found:
   - fixes_applied:
   - commits:
   - token_usage: prompt=?, completion=?, total=?
5. 如果本轮通过全部验收标准，明确输出：ROUND_SUCCEEDED。
6. 如果本轮未通过，明确输出：ROUND_FAILED，并给出下一轮计划。
