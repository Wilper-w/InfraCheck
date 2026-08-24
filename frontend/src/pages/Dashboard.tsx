import { useEffect, useState, useMemo, useRef, useCallback, type CSSProperties } from 'react';
import { Button, Grid, Table, Typography, Spin, Space, Tooltip, Empty, Message } from '@arco-design/web-react';
import { IconRefresh } from '@arco-design/web-react/icon';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import { dashboardApi, runApi, findingsApi } from '../api';
import type { DashboardSummary, TrendPoint, TopIssue, ResultStatus } from '../types';
import { VERDICT_TEXT, SERIES_META, TARGET_TYPE_TEXT } from '../constants';

const { Row, Col } = Grid;

const KPI_META = [
  { key: 'total' as const, label: '总检查数', cssVar: 'var(--c-primary)' },
  { key: 'normal' as const, label: '正常', cssVar: 'var(--c-normal)' },
  { key: 'abnormal' as const, label: '异常', cssVar: 'var(--c-abnormal)' },
  { key: 'unreachable' as const, label: '不可达', cssVar: 'var(--c-unreachable)' },
  { key: 'failed' as const, label: '检查失败', cssVar: 'var(--c-failed)' },
];

function parseEvidence(raw: string) {
  try {
    return JSON.parse(raw);
  } catch {
    return { detail: raw };
  }
}

const healthColor = (rate: number) =>
  rate >= 0.9 ? 'var(--c-normal)' : rate >= 0.6 ? 'var(--c-unreachable)' : 'var(--c-abnormal)';

/** 页头右侧的健康度摘要：替代原先独占 1/3 宽度的大环形卡 */
function HealthSummary({ rate, conclusion }: { rate: number; conclusion: string }) {
  const color = healthColor(rate);
  const r = 26;
  const c = 2 * Math.PI * r;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-3)' }}>
      <svg width="64" height="64" viewBox="0 0 64 64" aria-hidden>
        <circle cx="32" cy="32" r={r} fill="none" stroke="var(--c-fill)" strokeWidth="6" />
        <circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - rate)}
          transform="rotate(-90 32 32)"
          style={{ transition: 'stroke-dashoffset .6s ease' }}
        />
      </svg>
      <div>
        <div className="num" style={{ fontSize: 22, fontWeight: 650, color, lineHeight: 1.1 }}>
          {(rate * 100).toFixed(1)}%
        </div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--c-text-muted)', marginTop: 2 }}>
          健康率 · {conclusion}
        </div>
      </div>
    </div>
  );
}

/**
 * 趋势折线（按巡检次数）。每个数据点 = 一次巡检（run）的当次结果，非按天聚合；
 * 同一天多次巡检各占一个点。数据点不足时不绘图 —— 少于 4 个有效点的折线图
 * 只会呈现一条贴底平线 + 末端垂直拉升，误导且不可读。
 */
function TrendChart({ series }: { series: TrendPoint[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const W = 760;
  const H = 240;
  const P = { top: 16, right: 16, bottom: 28, left: 40 };

  const allMax = useMemo(
    () => Math.max(1, ...series.flatMap((p) => [p.normal, p.abnormal, p.unreachable, p.failed])),
    [series],
  );
  const maxVal = Math.ceil(allMax / 10) * 10 || 10;
  const cw = W - P.left - P.right;
  const ch = H - P.top - P.bottom;
  const x = useCallback(
    (i: number) => P.left + (series.length > 1 ? (i / (series.length - 1)) * cw : cw / 2),
    [series.length, cw],
  );
  const y = useCallback((v: number) => P.top + ch - (v / maxVal) * ch, [maxVal, ch]);

  const lines = useMemo(
    () =>
      SERIES_META.map((m) => ({
        ...m,
        path: series
          .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p[m.key]).toFixed(1)}`)
          .join(' '),
      })),
    [series, x, y],
  );

  const yTicks = useMemo(
    () => Array.from({ length: 5 }, (_, i) => Math.round((maxVal * i) / 4)),
    [maxVal],
  );

  const onMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!wrapRef.current || series.length === 0) return;
      const rect = wrapRef.current.getBoundingClientRect();
      const px = ((e.clientX - rect.left) / rect.width) * W;
      const idx = Math.round(((px - P.left) / cw) * (series.length - 1));
      setHover(Math.max(0, Math.min(series.length - 1, idx)));
    },
    [series.length, cw],
  );

  const shapePath = (cx: number, cy: number, type: string) => {
    if (type === 'square') return `M${cx - 3},${cy - 3} L${cx + 3},${cy - 3} L${cx + 3},${cy + 3} L${cx - 3},${cy + 3} Z`;
    if (type === 'triangle') return `M${cx},${cy - 4} L${cx + 4},${cy + 3} L${cx - 4},${cy + 3} Z`;
    if (type === 'diamond') return `M${cx},${cy - 4} L${cx + 4},${cy} L${cx},${cy + 4} L${cx - 4},${cy} Z`;
    return `M${cx - 3.5},${cy} A3.5,3.5,0,1,1 ${cx + 3.5},${cy} A3.5,3.5,0,1,1 ${cx - 3.5},${cy} Z`;
  };

  const activeRuns = series.filter(
    (p) => p.normal + p.abnormal + p.unreachable + p.failed > 0,
  );
  const latest = activeRuns[activeRuns.length - 1];

  if (series.length === 0) return <Empty description="暂无趋势数据" style={{ padding: 48 }} />;

  const summary = (
    <div className="trend-summary" style={{ marginTop: 'auto', padding: 'var(--s-4) 8px 0' }}>
      <div style={{ color: 'var(--c-text-muted)', fontSize: 'var(--fs-sm)', marginBottom: 'var(--s-3)' }}>
        {activeRuns.length < 4
          ? `目前仅 ${activeRuns.length} 次巡检有结果，数据点不足以呈现趋势；积累 4 次以上巡检后此处将自动显示折线图。`
          : `最近 ${activeRuns.length} 次巡检结果，折线图展示每次巡检的状态数量变化。`}
      </div>
      {latest && (
        <>
          {/* 与顶部 KPI 口径一致：每个点即「最近一次巡检」当次结果，
              每次巡检一个点，不再按天累计。 */}
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--c-text-2)', marginBottom: 'var(--s-2)' }}>
            {`${latest.date} 最近一次巡检（每个数据点 = 一次巡检，与上方「最近一次巡检」口径一致）`}
          </div>
          <div style={{ display: 'flex', gap: 'var(--s-6)', flexWrap: 'wrap' }}>
            {SERIES_META.map((m) => (
              <div key={m.key}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-xs)', color: 'var(--c-text-2)' }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: m.cssVar }} />
                  {m.label}
                </div>
                <div className="num" style={{ fontSize: 22, fontWeight: 650, marginTop: 4 }}>
                  {latest[m.key]}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  // 有效数据点 < 4：不绘制容易误导的折线，仅保留底部汇总。
  if (activeRuns.length < 4) {
    return (
      <div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column' }}>{summary}</div>
    );
  }

  const hp = hover !== null ? series[hover] : null;

  return (
    <div style={{ width: '100%' }}>
      <div className="trend-plot" ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
        <svg
          width="100%"
          viewBox={`0 0 ${W} ${H}`}
          style={{ display: 'block' }}
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
        >
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={P.left} x2={W - P.right} y1={y(t)} y2={y(t)} stroke="var(--c-border)" strokeDasharray="4 4" />
            <text x={P.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--c-text-muted)">
              {t}
            </text>
          </g>
        ))}
        {series.map((p, i) => (
          <text key={i} x={x(i)} y={H - 8} textAnchor="middle" fontSize="10" fill="var(--c-text-muted)">
            {i === 0 || i === series.length - 1 || i === Math.floor(series.length / 2)
              ? p.date.slice(5).replace('-', '/')
              : ''}
          </text>
        ))}
        {lines.map((l) => (
          <g key={l.key}>
            <path
              d={l.path}
              fill="none"
              stroke={l.cssVar}
              strokeWidth="2.2"
              strokeLinejoin="round"
              strokeLinecap="round"
              strokeDasharray={l.dash}
            />
          </g>
        ))}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={P.top} y2={P.top + ch} stroke="var(--c-border-strong)" strokeDasharray="3 3" />
            {lines.map((l) => (
              <path
                key={l.key}
                d={shapePath(x(hover), y(series[hover][l.key]), l.shape)}
                fill={l.cssVar}
                stroke={l.cssVar}
                strokeWidth="2"
              />
            ))}
          </g>
        )}
        </svg>
        {hp && hover !== null && (
          <div
            style={{
              position: 'absolute',
              left: `${(x(hover) / W) * 100}%`,
              top: 0,
              transform: 'translateX(8px)',
              background: 'var(--c-surface)',
              border: '1px solid var(--c-border)',
              borderRadius: 'var(--r-md)',
              boxShadow: 'var(--sh-lg)',
              padding: '8px 12px',
              fontSize: 'var(--fs-xs)',
              whiteSpace: 'nowrap',
              zIndex: 2,
              pointerEvents: 'none',
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{hp.date}</div>
            {SERIES_META.map((m) => (
              <div key={m.key} style={{ display: 'flex', alignItems: 'center', gap: 6, lineHeight: 1.7 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: m.cssVar }} />
                <span style={{ color: 'var(--c-text-muted)' }}>{m.label}</span>
                <span className="num" style={{ marginLeft: 'auto', fontWeight: 600 }}>{hp[m.key]}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {summary}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [topIssues, setTopIssues] = useState<TopIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [s, t, ti] = await Promise.all([
        dashboardApi.summary(),
        dashboardApi.trend(30),
        dashboardApi.topIssues(5),
      ]);
      setSummary(s);
      setTrend(t.series || []);
      setTopIssues(ti || []);
    } catch {
      /* 拦截器已提示 */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      // 后端异步执行巡检：POST /runs/trigger 立即返回 run_id，
      // 这里轮询 GET /runs/{id} 直到 finished/failed（CONTRACT §4），再刷新看板。
      const { run_id } = await runApi.trigger({ scope: 'all' });
      const deadline = Date.now() + 10 * 60 * 1000; // SSH 巡检较慢，上限 10 分钟
      while (Date.now() < deadline) {
        const run = await runApi.detail(run_id);
        if (run.status !== 'running') break;
        await new Promise((r) => setTimeout(r, 2000));
      }
      loadData();
    } catch {
      /* 拦截器已提示：触发或轮询失败时展示现有数据 */
    } finally {
      setTriggering(false);
    }
  };

  const handleTriage = async (issue: TopIssue, state: 'pending' | 'resolved' | 'ignored') => {
    try {
      await findingsApi.set({
        check_item_id: issue.check_item_id,
        object_type: issue.object_type,
        object_name: issue.object_name,
        environment_id: issue.environment_id,
        state,
      });
      Message.success(
        state === 'resolved' ? '已标记为已处理' : state === 'ignored' ? '已忽略该异常' : '已恢复为待处理',
      );
      loadData();
    } catch {
      /* 拦截器已提示 */
    }
  };

  if (loading && !summary)
    return (
      <div style={{ textAlign: 'center', paddingTop: 120 }}>
        <Spin size={40} tip="加载巡检数据中..." />
      </div>
    );

  const total = summary?.total ?? 0;
  const normal = summary?.normal ?? 0;
  const rate = total > 0 ? normal / total : 0;
  const envCount = summary?.environments.length ?? 0;
  const worstEnvs = [...(summary?.environments ?? [])].sort(
    (a, b) => (a.total > 0 ? a.normal / a.total : 0) - (b.total > 0 ? b.normal / b.total : 0),
  );
  const conclusion = rate >= 0.9 ? '整体健康' : rate >= 0.6 ? '部分异常' : '需立即处理';

  return (
    <div>
      <PageHeader
        title="总览"
        sub={`${envCount} 个环境 · ${total} 项检查`}
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-6)' }}>
            <HealthSummary rate={rate} conclusion={conclusion} />
            <Button type="primary" icon={<IconRefresh />} loading={triggering} onClick={handleTrigger}>
              立即巡检
            </Button>
          </div>
        }
      />

      <div className="kpi-grid">
        {KPI_META.map((k) => {
          const val = summary ? summary[k.key] : 0;
          const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0.0';
          return (
            <div key={k.key} className="kpi-card" style={{ '--kpi-color': k.cssVar } as CSSProperties}>
              <div className="kpi-label">
                <span className="kpi-dot" />
                {k.label}
              </div>
              <div className="kpi-value">{val}</div>
              <div className="kpi-sub">{k.key === 'total' ? '全部检查项' : `占总数 ${pct}%`}</div>
            </div>
          );
        })}
      </div>

      <Row className="equal-row" gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <div className="panel-card card-fill" style={{ width: '100%' }}>
            <div className="card-head">
              <div className="card-title">结果趋势</div>
              <div style={{ display: 'flex', gap: 'var(--s-4)' }}>
                {SERIES_META.map((m) => (
                  <span
                    key={m.key}
                    style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 'var(--fs-xs)', color: 'var(--c-text-2)' }}
                  >
                    <span style={{ width: 9, height: 9, borderRadius: 2, background: m.cssVar }} />
                    {m.label}
                  </span>
                ))}
              </div>
            </div>
            <div className="card-body">
              <TrendChart series={trend} />
            </div>
          </div>
        </Col>

        <Col xs={24} xl={8}>
          <div className="panel-card" style={{ width: '100%' }}>
            <div className="card-head">
              <div className="card-title">环境健康对比</div>
              <span className="sub-text">最差置顶</span>
            </div>
            <div className="card-body">
              {worstEnvs.length === 0 ? (
                <Empty description="暂无环境" />
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-4)' }}>
                  {worstEnvs.map((e) => {
                    const er = e.total > 0 ? e.normal / e.total : 0;
                    const ec = healthColor(er);
                    return (
                      <div key={e.environment_id}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--fs-sm)', marginBottom: 6 }}>
                          <span style={{ fontWeight: 550 }}>{e.name}</span>
                          <span className="num" style={{ fontWeight: 600, color: ec }}>
                            {(er * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div style={{ height: 6, borderRadius: 3, background: 'var(--c-fill)', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${er * 100}%`,
                              height: '100%',
                              background: ec,
                              borderRadius: 3,
                              transition: 'width .5s ease',
                            }}
                          />
                        </div>
                        <div className="sub-text" style={{ marginTop: 5 }}>
                          正常 {e.normal} · 异常 {e.abnormal} · 不可达 {e.unreachable} · 失败 {e.failed}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </Col>
      </Row>

      <div className="panel-card" style={{ marginTop: 'var(--s-4)' }}>
        <div className="card-head">
          <div>
            <div className="card-title">巡检异常项</div>
            <div className="sub-text" style={{ marginTop: 2 }}>
              最近一次巡检的异常 / 不可达 / 失败项，可逐项标记处置状态
            </div>
          </div>
          <Button type="text" size="small" onClick={() => navigate('/results')}>
            查看全部结果 →
          </Button>
        </div>
        <Table
          rowKey={(r) => `${r.check_item_id}-${r.object_type}-${r.object_name}-${r.environment_id}`}
          data={topIssues}
          pagination={false}
          scroll={{ x: 980 }}
          noDataElement={<Empty description="最近一次巡检无异常，一切正常" style={{ padding: 40 }} />}
          columns={[
            {
              title: '处置',
              dataIndex: 'state',
              width: 88,
              render: (v: string) => (
                <span className={`status-tag ${v === 'resolved' ? 'status-normal' : v === 'ignored' ? 'status-failed' : 'status-abnormal'}`}>
                  {v === 'resolved' ? '已处理' : v === 'ignored' ? '已忽略' : '待处理'}
                </span>
              ),
            },
            {
              title: '检查状态',
              dataIndex: 'status',
              width: 100,
              render: (v: string) => <StatusTag status={v as ResultStatus} />,
            },
            {
              title: '对象',
              dataIndex: 'object_name',
              render: (v: string, r: TopIssue) => (
                <Typography.Text bold>
                  <span className="meta-tag" style={{ marginRight: 8 }}>
                    {TARGET_TYPE_TEXT[r.object_type] || r.object_type}
                  </span>
                  {v}
                </Typography.Text>
              ),
            },
            { title: '环境', dataIndex: 'environment_name', width: 108 },
            {
              title: '判读',
              width: 220,
              ellipsis: true,
              render: (_: unknown, r: TopIssue) => {
                const e = parseEvidence(r.evidence);
                return (
                  <Tooltip
                    position="top"
                    content={<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(e, null, 2)}</pre>}
                  >
                    <span style={{ color: 'var(--c-text-2)', cursor: 'help' }}>{e.detail || e.verdict || '-'}</span>
                  </Tooltip>
                );
              },
            },
            {
              title: '判定',
              width: 116,
              render: (_: unknown, r: TopIssue) => {
                const e = parseEvidence(r.evidence);
                return <span className="meta-tag">{(e.verdict && VERDICT_TEXT[e.verdict]) || e.verdict || '-'}</span>;
              },
            },
            {
              title: '操作',
              key: 'action',
              width: 190,
              fixed: 'right',
              render: (_: unknown, r: TopIssue) =>
                r.state === 'pending' ? (
                  <Space>
                    <Button type="text" size="small" status="success" onClick={() => handleTriage(r, 'resolved')}>
                      标记已处理
                    </Button>
                    <Button type="text" size="small" onClick={() => handleTriage(r, 'ignored')}>
                      忽略
                    </Button>
                  </Space>
                ) : (
                  <Button type="text" size="small" onClick={() => handleTriage(r, 'pending')}>
                    恢复待处理
                  </Button>
                ),
            },
          ]}
        />
      </div>
    </div>
  );
}
