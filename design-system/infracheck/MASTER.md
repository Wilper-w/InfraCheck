# InfraCheck Design System — MASTER

> 企业级运维巡检控制台设计系统（明亮 · 数据优先 · 可信）。
> 栈：React 18 + Arco Design。来源：ui-ux-pro-max (B2B Service / Soft UI Evolution / Inter / Monitoring Line Chart)。
> 页面级覆盖优先：`pages/<page>.md` 存在则覆盖 Master。

## 视觉方向
明亮、可信、数据优先。白/浅灰蓝底 + 品牌海军蓝；数据密集但可扫读；状态色语义化（绿/红/琥珀/灰）。

## 颜色
| Token | 值 | 用途 |
|---|---|---|
| `--color-bg` | `#F5F7FA` | 应用背景 |
| `--color-surface` | `#FFFFFF` | 卡片/面板 |
| `--color-surface-2` | `#FAFBFC` | 表头/次级填充 |
| `--color-border` | `#E4E7EC` | 边框 |
| `--color-text` | `#0F172A` | 主文本 |
| `--color-text-2` | `#4B5563` | 次级文本 |
| `--color-text-muted` | `#8A919F` | 弱化/占位 |
| `--color-primary` | `#2563EB` | 主操作/CTA |
| `--color-primary-hover` | `#3B82F6` | 主色 hover |
| `--color-primary-soft` | `#EFF4FF` | 选中/强调填充 |
| `--color-status-normal` | `#16A34A` | 正常 |
| `--color-status-abnormal` | `#DC2626` | 异常 |
| `--color-status-unreachable` | `#F59E0B` | 不可达 |
| `--color-status-failed` | `#9CA3AF` | 检查失败 |

## 字体
- Latin：Inter（题/正文）；代码/证据/ID：Fira Code / JetBrains Mono。
- 中文回退：PingFang SC / Microsoft YaHei / Noto Sans SC。
- 基准 14px，行高 1.5；正文 ≥ 12px；KPI 数字用 tabular-nums。
- 字号梯度：24 / 20 / 16 / 14 / 12。

## 圆角
- 控件 6px；卡片 8px；模态/大面板 12px；登录大卡 14px。

## 间距（4 基刻度，密度 7/10）
- 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48
- 内容区 24px；卡片内边距 20px；栅格槽 16px；区块间隔 16–20px。

## 卡片
白底 + 1px 边框 + `0 1px 2px` 投影；hover `0 6px 18px`；头部标题 15/600 + 副文 12 灰。

## 按钮
主按钮实心品牌蓝 `#2563EB`，高 32/40，圆角 6，字号 14；统一 loading + cursor:pointer + 显式 focus 环。

## 导航
浅色侧栏 224px 白底 + 右分隔线；选中项品牌蓝 soft 填充 + 左侧 3px 指示条；顶栏 56px 白 + 面包屑/账号；菜单项高 40，hover 200ms。

## 动效 / 可达性
交互过渡 150–300ms；遵循 prefers-reduced-motion；键盘焦点可见；图表多系列用线型区分（实/虚/点）不仅靠颜色；文本对比 ≥4.5:1。
