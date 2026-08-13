# InfraCheck 开发契约（CONTRACT）

本文件是前后端并行开发的**唯一事实来源**。后端（backend/）与前端（frontend/）都必须严格遵循本契约。
领域词汇见 `CONTEXT.md`。

## 1. 架构总览

前后端分离。
- **后端**：Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT(pyjwt) + APScheduler + uvicorn。默认 SQLite（本地开发），生产经 `DATABASE_URL` 用 PostgreSQL。巡检执行引擎含 **dryrun**（本地可跑、确定性假数据）与 **ssh**（经跳板机 ProxyJump 真连）两种 transport，由环境变量 `RUNNER_TRANSPORT` 切换。
- **前端**：React + TypeScript + Vite + @arco-design/web-react。消费 REST API。
- 后端启动时若数据库为空则**自动播种**一套演示数据（见 §5），保证 dryrun 端到端可跑。

/api 前缀保留给后端；前端 dev 用 Vite proxy 转发 `/api` → 后端。

## 2. 通用约定

- 所有请求体/响应体为 JSON（UTF-8）。
- 时间统一 ISO8601 UTC 字符串。
- 认证：`Authorization: Bearer <JWT>`。除登录与健康检查外，所有接口校验 JWT。
- 响应错误：`{"detail": "..."}` + 对应 HTTP 状态码。
- 列表接口默认 `?page=1&page_size=20`，返回 `{"items":[...], "total": int, "page": int, "page_size": int}`。

## 3. 数据模型（SQLAlchemy，表名 snake_case）

**environments**：id(int PK)｜name(str unique)｜os_flavor(str: "ubuntu"|"centos")｜description(str)｜created_at
**physical_nodes**：id｜environment_id(FK)｜hostname(str)｜ip(str)｜os_flavor(str, 可空，空则继承环境)｜created_at｜unique(environment_id, hostname)
**system_services**：id｜environment_id(FK)｜node_id(FK 可空)｜name(str: nginx/keepalived/mysql/haproxy/...)｜port(int 可空)｜enabled(bool)｜probe_mode(str: "systemd"|"port"|"vip"，默认 systemd)｜probe_target(str 可空，vip 模式存虚拟 IP)

> `enabled=false` 的服务**不进入巡检目标**（见 §6 目标解析）。
> `probe_mode=port` 必须有 `port`，`probe_mode=vip` 必须有 `probe_target`，否则 422。
**clusters**：id｜environment_id(FK)｜name(str)｜api_endpoint(str)｜created_at
**namespaces**：id｜cluster_id(FK)｜name(str)｜unique(cluster_id,name)
**pods**：id｜namespace_id(FK)｜name(str)｜labels(str JSON 可空)
**check_items**：id｜name(str)｜target_type(str: physical|service|cluster|pod)｜os_flavor(str 可空=all)｜description(str)｜enabled(bool)｜config(str JSON, 阈值等)
**runs**：id｜trigger(str: scheduled|manual)｜triggered_by(str=巡检人账号)｜started_at｜finished_at(可空)｜status(str: running|finished|failed)
**check_results**：id｜run_id(FK)｜check_item_id(FK)｜object_type(str)｜object_name(str)｜environment_id(FK)｜os_flavor(str 可空)｜status(str: normal|abnormal|unreachable|failed)｜evidence(str, 原始证据文本)｜captured_at
**reports**：id｜run_id(FK)｜rendered_by(str 账号)｜generated_at｜html_path(str)｜md_path(str)
**audit_logs**：id｜actor(str 账号)｜action(str)｜target_ref(str 可空)｜detail(str)｜created_at

`create_all()` 建表；`os_flavor` 取值 `ubuntu`/`centos`。

## 4. REST API

### 认证 /auth
- `POST /api/auth/login`  请求 `{"account": str}`（企业微信 SSO 在真模式下换取账号；mock 模式直接用该 account）。响应 `{"token": str, "account": str}`。
- `GET /api/auth/me`  (需 JWT) 响应 `{"account": str}`。

### 环境 /environments
- `GET /api/environments`
- `POST /api/environments`  `{"name","os_flavor","description?"}`
- `PUT /api/environments/{id}`  同上可部分更新
- `DELETE /api/environments/{id}`
- `GET /api/environments/{id}/summary` 响应 `{"environment_id","environment_name","os_flavor","total","normal","abnormal","unreachable","failed"}`（基于该环境最近一次 run 的结果统计；无则全 0）

### 物理机 /environments/{env_id}/nodes
- `GET /api/environments/{env_id}/nodes`
- `POST /api/environments/{env_id}/nodes`  `{"hostname","ip","os_flavor?"}`
- `DELETE /api/environments/{env_id}/nodes/{node_id}`

### 系统服务 /environments/{env_id}/services
- `GET /api/environments/{env_id}/services`
- `POST /api/environments/{env_id}/services`  `{"name","node_id?","port?","enabled?","probe_mode?","probe_target?"}`
- `PUT /api/environments/{env_id}/services/{service_id}`  同上全部字段可选
- `POST /api/environments/{env_id}/services/{service_id}/toggle` → 翻转 `enabled`，返回 ServiceOut
- `DELETE /api/environments/{env_id}/services/{service_id}`

### K8s /environments/{env_id}/clusters
- `GET /api/environments/{env_id}/clusters`
- `POST /api/environments/{env_id}/clusters`  `{"name","api_endpoint?"}`
- `GET /api/clusters/{cluster_id}/namespaces`
- `POST /api/clusters/{cluster_id}/namespaces`  `{"name"}`
- `GET /api/namespaces/{ns_id}/pods`
- `POST /api/namespaces/{ns_id}/pods`  `{"name","labels?"}`

### 巡检项 /check-items
- `GET /api/check-items?enabled=&target_type=`
- `POST /api/check-items`  `{"name","target_type","os_flavor?","description?","config?"}`
- `PUT /api/check-items/{id}`
- `DELETE /api/check-items/{id}`
- `POST /api/check-items/{id}/toggle` 取反 enabled

### 巡检执行与结果 /runs /results
- `POST /api/runs/trigger` 请求 `{"scope":"all"|"environment"|"check"`, `"environment_id"?`, `"check_item_id"?`}（manual 触发）。响应 `{"run_id": int}`。
- `GET /api/runs`  列表（含 `triggered_by`、`status`、`started_at`）
- `GET /api/runs/{id}`  详情（含 `results` 摘要计数）
- `GET /api/runs/{id}/results?status=&object_type=&page=`  该次结果明细（含 evidence）
- `GET /api/results/latest`  全平台最近一次 run 的结果（按环境聚合，用于大盘）

### 大盘与趋势 /dashboard
- `GET /api/dashboard/summary` 响应：`{"generated_at", "total", "normal", "abnormal", "unreachable", "failed", "environments":[{environment_id, name, abnormal, unreachable, failed, total}]}`
- `GET /api/dashboard/trend?days=30` 响应 `{"series":[{"date":"YYYY-MM-DD","normal":n,"abnormal":n,"unreachable":n,"failed":n}]}`（按天的所有 run 结果汇总）

### 报告 /reports
- `GET /api/reports`  列表（含 `run_id`、`rendered_by`、`generated_at`、`html_path`、`md_path`）
- `GET /api/reports/{id}/html` → 返回 text/html（报告 HTML 内容）
- `GET /api/reports/{id}/markdown` → 返回 text/plain（Markdown 内容）

### 审计 /audit
- `GET /api/audit?actor=&page=` 响应 items：`{"actor","action","target_ref","detail","created_at"}`

## 5. 启动播种（后端）

启动时若 `environments` 表为空，写入：
- 环境：`env-01`(ubuntu, 4 台节点)、`env-02`(ubuntu, 3 台)、`env-03`(ubuntu, 3 台)、`env-04`(ubuntu, 3 台)、`env-05`(centos, 3 台节点)
- 每台节点名 `node-<env>-<i>`，ip 形如 `10.0.<env#>.<i>`；节点 os_flavor 继承环境。
- 每个环境 4 个系统服务各一个：nginx、keepalived、mysql、haproxy，挂其中一台节点。
- `env-01` 建一个集群 `k8s-prod` + 命名空间 `default`、`ai`、`infra`，各含 2~3 个 pod（如 etcd、one-api、new-api、redis）。其余环境各一个集群 + default 命名空间 + 少量 pod。
- 巡检项若干，覆盖四类对象，`enabled=true`。

## 6. 巡检执行引擎

- **CheckItem 按 target_type 注册**；同语义按 `os_flavor` 分派命令（如 systemd 状态、磁盘使用率、内存、负载）。
- **目标解析**：`target_type=service` 只纳入 `enabled=true` 的服务；停用即退出巡检范围。
- **服务探测按 `probe_mode` 二次分派**（ssh transport）：

  | probe_mode | 命令 | 适用 |
  |---|---|---|
  | `systemd` | `systemctl is-active <name>` | 标准 systemd 托管服务 |
  | `port` | `ss -ltnH 'sport = :<port>' \| grep -q LISTEN` | 有监听端口的服务，能证明真正对外提供能力 |
  | `vip` | `ip -o addr show \| grep -qw <probe_target>` | keepalived 等漂 VIP 的服务 |

  vip 模式的语义要点：keepalived **进程存活不等于正常** —— VIP 未绑在本机同样是故障，因此探测的是地址绑定而非进程。
  `port` 模式缺 `port`、`vip` 模式缺 `probe_target` 时回落到 `systemd`，避免拼出无法执行的命令。
- `RUNNER_TRANSPORT=dryrun`（默认）：对每个对象按确定性规则产出结果（尽量让结果覆盖 normal/abnormal/unreachable/failed 四态，便于展示）。
- `RUNNER_TRANSPORT=ssh`：读 `JUMP_HOST`/`JUMP_USER`/`JUMP_KEY`，经 ProxyJump 到目标执行。
- 每次 run 触发时写 audit，actor 来自 JWT 的 `account`；run 结束后自动生成 HTML/Markdown 报告并写 reports + audit。

## 7. 前后端请求示例（契约锚点）

```
POST /api/auth/login {"account":"zhangsan"} → {"token":"...","account":"zhangsan"}
GET /api/dashboard/summary  (Bearer)
POST /api/runs/trigger {"scope":"all"}
GET /api/runs  (轮询，status 变 finished 后)
GET /api/runs/{id}/results?status=abnormal
GET /api/reports  → 取最新 report，GET /api/reports/{id}/html 在 iframe 展示
```

## 8. 约定目录

- `backend/`：FastAPI 工程（`app/` 包含 models、schemas、api、engine、runner、reports、auth、scheduler、seed）。
- `frontend/`：Vite + React + TS + Arco。
- 前端页面：登录、大盘 Dashboard、结果浏览 Results、报告 Reports、配置 Configuration、审计 Audit。

后端路由统一挂 `/api`。CORS 允许 localhost:5173。
