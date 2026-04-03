# ForgeLoopAI v0.1 UI 设计

## 1. 目标

UI 用于回答五个核心问题：

- 现在处于第几轮、哪个阶段
- 之前跑了几轮，每轮结果如何
- 每轮发现了什么问题
- 每轮修复了什么 bug、产生了哪些 commit
- 每轮和全局消耗了多少 token 与费用

## 2. 信息架构

v0.1 采用四个页面：

1. **Run Overview**
2. **Rounds & Issues**
3. **Fixes & Commits**
4. **Cost & Tokens**

## 3. 页面设计

### 3.1 Run Overview

展示字段：

- run_id
- project / branch / start_time / duration
- overall_status
- current_round_index
- current_phase
- gate_status（是否等待确认）

交互：

- 继续执行（approve）
- 拒绝执行（reject）
- 跳转到当前轮详情

### 3.2 Rounds & Issues

按轮次展示列表：

- round_index
- round_status
- discovered_issues_count
- fixed_issues_count
- created_commits_count
- round_token_total

每轮展开后展示：

- issue_id / symptom / root_cause / severity
- issue_status（open/fixed/verified）

### 3.3 Fixes & Commits

以时间线展示：

- fix_id
- 对应 issue_id
- 修复策略摘要
- patch 摘要
- commit_sha / commit_message
- regression_result

### 3.4 Cost & Tokens

展示维度：

- run 级总 token / 总费用
- round 级 token / 费用
- phase 级 token 分布（build/test/repair）
- 模型维度费用（按 model 聚合）

告警：

- 超预算预警
- 超阈值重试预警

## 4. 后端接口（v0.1 草案）

- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/rounds`
- `GET /api/runs/{run_id}/issues`
- `GET /api/runs/{run_id}/fixes`
- `GET /api/runs/{run_id}/commits`
- `GET /api/runs/{run_id}/cost`
- `POST /api/runs/{run_id}/approve`
- `POST /api/runs/{run_id}/reject`

## 5. 数据对象（UI 最小集）

### 5.1 Round

- round_index
- phase
- status
- started_at
- ended_at
- issue_count
- fix_count
- commit_count
- token_total
- usd_total

### 5.2 Issue

- issue_id
- round_index
- title
- symptom
- root_cause
- severity
- status

### 5.3 FixCommit

- fix_id
- issue_id
- round_index
- strategy
- commit_sha
- commit_message
- regression_passed

### 5.4 Cost

- run_id
- model
- prompt_tokens
- completion_tokens
- total_tokens
- total_usd

## 6. v0.1 实现建议

- 先做只读 UI，控制动作仅支持 approve/reject
- 数据源直接读取审计产物（events.jsonl、rounds.json、cost.json）
- 前端框架可后置，先完成接口与数据协议
