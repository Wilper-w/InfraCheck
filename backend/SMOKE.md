# InfraCheck 后端冒烟测试记录（SMOKE）

> 本文件记录后端实际执行的端到端验证命令与关键输出，作为集成阶段证据。
> 环境：macOS / Python 3.12.12 / SQLite（默认）/ `RUNNER_TRANSPORT=dryrun`。

## 0. 前置准备

```bash
cd backend
# 创建虚拟环境（本机 python3 为 uv shim，使用 uv 创建）
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python fastapi 'uvicorn[standard]' 'sqlalchemy>=2.0' \
    'pydantic>=2' pyjwt python-multipart cryptography asyncssh apscheduler pytest httpx

# 单元/验收测试（TestClient，内存 SQLite）
.venv/bin/python -m pytest -q
```

测试输出：

```
27 passed, 1 warning in 0.37s
```

覆盖：登录拿 token；未带 token 访问返回 401；触发 dryrun 巡检后 run 状态 finished；
结果覆盖 normal/abnormal/unreachable/failed 四态；报告 HTML/Markdown 可取回；审计有记录；
分页结构；环境摘要；巡检项 toggle/filter；仪表盘趋势。

## 1. 启动服务

```bash
cd backend
SCHEDULER_ENABLED=false .venv/bin/uvicorn app.main:app --port 8000
```

启动日志：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

启动时自动 `create_all` 建表并播种 5 套环境（4 ubuntu + 1 centos）、节点、系统服务、
集群/命名空间/pod、巡检项。

## 2. 登录拿 token

```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' -d '{"account":"zhangsan"}'
```

响应：

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ6aGFuZ3NhbiIsImFjY291bnQiOiJ6aGFuZ3NhbiIsImlhdCI6MTc4NjYxNjE4NSwiZXhwIjoxNzg2NzAyNTg1fQ.c_vj5d891h8aRt99-7m0nWx8tgf4thYm2OQ-Lburto0",
  "account": "zhangsan"
}
```

## 3. 未带 token 访问返回 401

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/dashboard/summary
```

输出：

```
401
```

## 4. 触发 dryrun 巡检

```bash
curl -s -X POST http://127.0.0.1:8000/api/runs/trigger \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"scope":"all"}'
```

响应：

```json
{"run_id": 1}
```

## 5. 查看 run 详情（状态 finished + 四态计数）

```bash
curl -s http://127.0.0.1:8000/api/runs/1 -H "Authorization: Bearer $TOKEN"
```

响应：

```json
{
  "id": 1,
  "trigger": "manual",
  "triggered_by": "zhangsan",
  "started_at": "2026-08-13T10:16:25.782858",
  "finished_at": "2026-08-13T10:16:25.792669",
  "status": "finished",
  "results": {
    "abnormal": 14,
    "failed": 30,
    "normal": 22,
    "unreachable": 24
  }
}
```

run 状态从 `running` → `finished`；结果覆盖 normal/abnormal/unreachable/failed 四态。

## 6. 查看结果明细（含 evidence + 四态）

```bash
curl -s "http://127.0.0.1:8000/api/runs/1/results?page=1&page_size=200" \
  -H "Authorization: Bearer $TOKEN"
```

状态分布（90 条结果，四态全覆盖）：

```
total: 90
{'unreachable': 24, 'abnormal': 14, 'failed': 30, 'normal': 22}
sample evidence: {"check": "节点存活与负载", "object": "node-env-01-1(10.0.1.1)", "os_flavor": "ubuntu", "transport": "dryrun", ...}
```

## 7. 大盘汇总

```bash
curl -s http://127.0.0.1:8000/api/dashboard/summary -H "Authorization: Bearer $TOKEN"
```

响应：

```json
{
  "generated_at": "2026-08-13T10:16:25.901902Z",
  "total": 90,
  "normal": 22,
  "abnormal": 14,
  "unreachable": 24,
  "failed": 30,
  "environments": [
    {"environment_id": 1, "name": "env-01", "abnormal": 6, "unreachable": 6, "failed": 7, "total": 26},
    {"environment_id": 2, "name": "env-02", "abnormal": 3, "unreachable": 3, "failed": 6, "total": 16},
    {"environment_id": 3, "name": "env-03", "abnormal": 1, "unreachable": 2, "failed": 8, "total": 16},
    {"environment_id": 4, "name": "env-04", "abnormal": 2, "unreachable": 6, "failed": 5, "total": 16},
    {"environment_id": 5, "name": "env-05", "abnormal": 2, "unreachable": 7, "failed": 4, "total": 16}
  ]
}
```

## 8. 取回报告（HTML + Markdown）

```bash
# 报告列表
curl -s http://127.0.0.1:8000/api/reports -H "Authorization: Bearer $TOKEN"
# → {"items":[{"id":1,"run_id":1,"rendered_by":"zhangsan",...}],"total":1,...}

# HTML 报告
curl -s http://127.0.0.1:8000/api/reports/1/html -H "Authorization: Bearer $TOKEN"
# content-type: text/html; charset=utf-8
# 首行: <!DOCTYPE html>

# Markdown 报告
curl -s http://127.0.0.1:8000/api/reports/1/markdown -H "Authorization: Bearer $TOKEN"
# content-type: text/plain; charset=utf-8
# 首行: # InfraCheck 巡检报告
```

报告内容（Markdown 头部）：

```markdown
# InfraCheck 巡检报告

- 巡检编号 (Run ID): **1**
- 触发方式: manual
- 触发人: zhangsan
- 开始时间: 2026-08-13 10:16:25.782858
- 结束时间: 2026-08-13 10:16:25.792669+00:00
- 状态: finished
```

## 9. 审计日志

```bash
curl -s "http://127.0.0.1:8000/api/audit?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

响应：

```json
{
  "items": [
    {
      "id": 2,
      "actor": "zhangsan",
      "action": "report.generate",
      "target_ref": "report:1",
      "detail": "run 1 report rendered (html+md)",
      "created_at": "2026-08-13T10:16:25.802203"
    },
    {
      "id": 1,
      "actor": "zhangsan",
      "action": "run.trigger",
      "target_ref": "run:1",
      "detail": "manual trigger scope=all",
      "created_at": "2026-08-13T10:16:25.783610"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 10
}
```

审计记录了：触发巡检（actor=JWT account=zhangsan）、报告生成，符合契约 §6。

## 验收对照

| 验收项 | 状态 |
| --- | --- |
| `.venv/bin/python -m pytest -q` 全绿 | ✅ 27 passed |
| 登录拿 token | ✅ §2 |
| 未带 token 返回 401 | ✅ §3 |
| 触发 dryrun 后 run finished | ✅ §5 |
| 结果覆盖四态 | ✅ normal/abnormal/unreachable/failed |
| 报告 HTML/MD 可取回 | ✅ §8 |
| 审计有记录 | ✅ §9 |
| uvicorn 启动无错 | ✅ §1 |
| `/api/dashboard/summary` 结构符合契约 | ✅ §7 |
