<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="InfraCheck 基础设施巡检平台：一次触发，经跳板机与多跳链路巡检多个互不连通的内网部署环境，对物理机、系统服务、K8s 集群/Pod、bond 与 mysql 集群自动判定状态、留存证据并出具可归档报告">
</p>

InfraCheck 是一个企业级基础设施巡检平台：通过一台能同时访问所有目标网络的**跳板机**与多跳 SSH 链路，一次触发即可巡检**多个网络互不连通**的内网部署环境。平台覆盖 `物理机 / 系统服务 / K8s 集群 / Pod` 四类对象，每条结果都判定为四种语义严格区分状态之一：`正常` / `异常` / `不可达` / `检查失败`，并自动生成可浏览、可归档的巡检报告与完整审计记录。

无外部服务依赖，开箱即用：默认 `dryrun` 数据源启动即自动播种演示环境，克隆仓库跑起来就能看到端到端效果；切换 `ssh` 运输层即可对接真实环境。

---

## 演示

真实健康大盘（环境健康对比 · 四态 KPI · 带证据的异常项处置 · 按巡检次数的结果趋势）：

<p align="center">
  <img src="./assets/readme/dashboard.webp" width="100%" alt="InfraCheck 健康大盘：总检查数、正常/异常/不可达/检查失败四态 KPI、健康环、环境健康对比、巡检异常项表格与结果趋势">
</p>

## 它解决了什么

企业通常维护多个**彼此网络互不连通**的部署环境（生产、内网隔离区等），传统巡检需要逐个环境登录、手工执行命令、人工比对结果。InfraCheck 只依赖一台同时连通全部环境的跳板机，由平台经它触达所有目标：

- **一次触发，全量覆盖**——按需或定时触发，跨环境统一执行，无需逐台登录。
- **多点触达，拓扑灵活**——支持跳板机直达、经网关的多跳链路、以及经跳板机自身 SSH 别名三种接入方式，适配不同网络拓扑。
- **判定带证据**——每条结果都携带原始证据（命令输出、返回码、指标值、日志片段），可追溯、可复盘。
- **结果四态明确**——`正常` / `异常` / `不可达` / `检查失败` 语义严格区分，异常项在异常表逐条处置，处置状态持续跟踪。
- **报告自动归档**——每次巡检自动生成 HTML（平台内浏览）与 Markdown（归档 / 进仓库）双格式报告。
- **全流程可审计**——谁在何时触发哪次巡检、报告由哪个账号生成，均有审计日志。

## 核心能力

| 能力 | 说明 |
|------|------|
| 多对象巡检 | `物理机`（存活 / 负载 / 磁盘 / 内存）· `系统服务`（systemd / port / vip 三态探测）· `K8s 集群`（节点与 Pod 健康）· `Pod`（phase / ready / restartCount） |
| 多跳 SSH 接入 | 经跳板机 `ProxyJump`：直达节点、经 `SSH_GATEWAY` 网关多跳、或经跳板机自身 SSH 别名（`SSH_NODE_COMMAND`）三种形态 |
| Ansible 聚合 | `COLLECTOR=ansible` 时在网关节点上把只读脚本经 ansible `-m script` fan-out 到全节点，一次拉取整环境状态 |
| 集群专项 | `bond0` 双网卡健康检查（单网卡环境如实上报"非异常"而非误报）· `mysql` 集群 `wsrep_*` 状态（密码经 gitignored 的 `.env` 注入，不进源码/日志） |
| 状态语义 | 四种状态各有运维含义与处置方式区分，`vip` 探测考量"地址绑定而非进程存活"（keepalived 进程在 ≠ VIP 正常） |
| 报告与审计 | HTML + Markdown 双格式自动归档，巡检触发与报告生成全程留痕 |

## 快速开始

用 Docker Compose 一键起前后端（默认 `dryrun`，含演示数据）：

```bash
docker compose up -d
# 前端  http://localhost:8080
# 后端  http://localhost:8000
```

登录页输入任意账号即可（`AUTH_MODE=mock`）。进入大盘后点「立即巡检」，即可看到一次全量巡检的结果与报告。

### 本地开发

```bash
# 后端（Python 3.12）
cd backend && uv sync
SCHEDULER_ENABLED=false uv run uvicorn app.main:app --port 8000

# 前端（React + Vite，dev 代理 /api → 8000）
cd frontend && npm install && npm run dev
```

### 对接真实环境

在 `backend/.env`（`AUTH_MODE=mock` 之外的真实接入配置，含模板见 `backend/.env.example`）中按拓扑选择接入形态：

```yaml
# 平台 → 跳板机（免密，用本机 ~/.ssh）
RUNNER_TRANSPORT: ssh
JUMP_HOST: your-jump-host    # 唯一能访问全部环境的节点
JUMP_KEY: /run/secrets/jump_key

# 跳板机 → 节点：三种形态任选——
#   直达：jump 透明连接节点（平台公钥在节点上）
#   网关：经 SSH_GATEWAY 多跳到节点
SSH_GATEWAY: node-gateway
SSH_GATEWAY_PORT: 30122
#   别名：复用跳板机自身 ssh 别名/包装器（如 lf）触达节点
SSH_VIA_JUMP_SHELL: 1
SSH_NODE_COMMAND: ssh -o BatchMode=yes root@{address}

# 聚合巡检（可选）与数据库
COLLECTOR: ansible                     # 在网关节点经 ansible 聚合巡检
MYSQL_DEFAULT_PW: <mysql 集群密码>     # 仅本地 .env，gitignored
DATABASE_URL: postgresql://...         # 生产改用 PostgreSQL
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · JWT · APScheduler · asyncssh |
| 前端 | React 18 · TypeScript · Vite · Arco Design |
| 部署 | Docker Compose · SQLite（开发）/ PostgreSQL（生产）· 可选用 Ansible 聚合 |

## 结构

```
backend/   FastAPI：models / api / engine / runner / reports / auth / scheduler / seed
frontend/  React：登录 · 健康大盘 · 巡检结果 · 报告 · 配置 · 审计
design-system/infracheck/   设计令牌与组件规范
```

前端页面：`/login` 登录，`/` 健康大盘，`/results` 结果浏览，`/reports` 报告归档，`/configuration` 配置，`/audit` 审计日志。

## 文档

- [`CONTRACT.md`](./CONTRACT.md)——前后端契约的唯一事实来源（数据模型 / REST API / 契约锚点）
- [`design-system/infracheck/MASTER.md`](./design-system/infracheck/MASTER.md)——设计令牌与交互规范
- [`backend/SMOKE.md`](./backend/SMOKE.md)——后端端到端冒烟测试记录

## 项目状态

面向企业内部使用，尚未公开发布。核心闭环（巡检执行 → 结果判定 → 报告归档 → 审计）已端到端跑通并通过冒烟测试与验收测试。
