# InfraCheck 前端

React + TypeScript + Vite + Arco Design 巡检平台前端。

## 技术栈

- React 18 + TypeScript
- Vite 6（构建 + dev server）
- @arco-design/web-react（UI 组件库）
- react-router-dom（路由）
- axios（HTTP 请求）

## 开发

```bash
npm install
npm run dev      # 启动 dev server，默认 http://localhost:5173
npm run build    # tsc 类型检查 + vite 生产构建
npm run preview  # 预览构建产物
```

## API 代理与 CORS

- **dev 模式**：`vite.config.ts` 配置了 proxy，将 `/api` 前缀的请求转发到后端 `http://localhost:8000`，前端请求同源（localhost:5173），无需关心 CORS。
- **后端 CORS**：按 `CONTRACT.md` §8，后端已允许 `localhost:5173`。dev 经 proxy 可完全绕过同源限制。
- **生产模式**：构建产物（`dist/`）可由后端 FastAPI 静态托管，`/api` 由后端提供，同源无 CORS 问题。

所有 API 调用统一走 `src/api/client.ts` 的 axios 实例：请求拦截器自动注入 `Authorization: Bearer <token>`，响应拦截器在 401 时清除 token 并跳转登录页。

## 页面与路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | POST `/api/auth/login`，存 token 到 localStorage |
| `/` | 健康大盘 | GET `/api/dashboard/summary` + `/api/dashboard/trend`，立即巡检 POST `/api/runs/trigger` |
| `/results` | 结果浏览 | GET `/api/runs` 列表，点开 GET `/api/runs/{id}` + `/api/runs/{id}/results` |
| `/reports` | 报告 | GET `/api/reports` 列表，Modal 内 iframe 查看 HTML，下载 Markdown |
| `/configuration` | 配置 | 环境/物理机/系统服务/巡检项 Tab CRUD |
| `/audit` | 审计 | GET `/api/audit` 表格，按 actor 筛选 |

API 路径与 `CONTRACT.md` §4 完全一致。

## 认证流程

1. 登录页输入账号 → `POST /api/auth/login` → 返回 `{token, account}`，存入 `localStorage`。
2. 后续所有请求自动带 `Authorization: Bearer <token>`。
3. 任一接口返回 401 → 清除 token → 跳转 `/login`。
