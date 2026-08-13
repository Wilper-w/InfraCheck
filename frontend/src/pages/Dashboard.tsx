import { useEffect, useState, useMemo, useRef, useCallback, type CSSProperties } from 'react';
import {
  Button,
  Grid,
  Progress,
  Table,
  Typography,
  Spin,
  Space,
  Tag,
  Tooltip,
  Empty,
  Message,
} from '@arco-design/web-react';
import {
  IconApps,
  IconCheckCircle,
  IconCloseCircle,
  IconExclamationCircle,
  IconInfoCircle,
  IconRefresh,
} from '@arco-design/web-react/icon';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import { dashboardApi, runApi, findingsApi } from '../api';
import type { DashboardSummary, TrendPoint, TopIssue, ResultStatus } from '../types';
import { VERDICT_TEXT } from '../constants';

const { Row, Col } = Grid;

const SERIES_META = [
  { key: 'normal' as const, label: '正常', color: '#16a34a', dash: undefined, shape: 'circle' },
  { key: 'abnormal' as const, label: '异常', color: '#dc2626', dash: '6 4', shape: 'square' },
  { key: 'unreachable' as const, label: '不可达', color: '#f59e0b', dash: '2 3', shape: 'triangle' },
  { key: 'failed' as const, label: '检查失败', color: '#9ca3af', dash: '4 3', shape: 'diamond' },
];

const KPI_META = [
  { key: 'total' as const, label: '总检查数', color: '#2563eb', icon: <IconApps /> },
  { key: 'normal' as const, label: '正常', color: '#16a34a', icon: <IconCheckCircle /> },
  { key: 'abnormal' as const, label: '异常', color: '#dc2626', icon: <IconCloseCircle /> },
  { key: 'unreachable' as const, label: '不可达', color: '#f59e0b', icon: <IconExclamationCircle /> },
  { key: 'failed' as const, label: '检查失败', color: '#9ca3af', icon: <IconInfoCircle /> },
];

const TARGET_TEXT: Record<string, string> = { physical: '物理机', service: '系统服务', cluster: '集群', pod: 'Pod' };

function parseEvidence(raw: string) {
  try { return JSON.parse(raw); } catch { return { detail: raw }; }
}

/* ---- 环形健康度（SVG donut）---- */
function HealthDonut({ normal, total }: { normal: number; total: number }) {
  const rate = total > 0 ? normal / total : 0;
  const color = rate >= 0.9 ? '#16a34a' : rate >= 0.6 ? '#f59e0b' : '#dc2626';
  const r = 52, c = 2 * Math.PI * r;
  const offset = c * (1 - rate);
  return (
    <svg width="140" height="140" viewBox="0 0 140 140">
      <circle cx="70" cy="70" r={r} fill="none" stroke="#e4e7ec" strokeWidth="10" />
      <circle cx="70" cy="70" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={offset} transform="rotate(-90 70 70)"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
      <text x="70" y="66" textAnchor="middle" fontSize="22" fontWeight="700" fill={color}>
        {(rate * 100).toFixed(1)}%
      </text>
      <text x="70" y="86" textAnchor="middle" fontSize="11" fill="#8a919f">健康率</text>
    </svg>
  );
}

/* ---- 交互式折线趋势图（线型 + 形状标记 + hover）---- */
function TrendChart({ series }: { series: TrendPoint[] }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const W = 760, H = 280;
  const P = { top: 18, right: 16, bottom: 32, left: 44 };

  const allMax = useMemo(() =>
    Math.max(1, ...series.flatMap((p) => [p.normal, p.abnormal, p.unreachable, p.failed])), [series]);
  const maxVal = Math.ceil(allMax / 10) * 10;
  const cw = W - P.left - P.right, ch = H - P.top - P.bottom;
  const x = (i: number) => P.left + (series.length > 1 ? (i / (series.length - 1)) * cw : cw / 2);
  const y = (v: number) => P.top + ch - (v / maxVal) * ch;

  const lines = useMemo(() => SERIES_META.map((m) => ({
    ...m,
    path: series.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p[m.key]).toFixed(1)}`).join(' '),
  })), [series, maxVal]);

  const yTicks = useMemo(() => {
    const n = 4; return Array.from({ length: n + 1 }, (_, i) => Math.round((maxVal * i) / n));
  }, [maxVal]);

  const onMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!wrapRef.current || series.length === 0) return;
    const rect = wrapRef.current.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const idx = Math.round(((px - P.left) / cw) * (series.length - 1));
    setHover(Math.max(0, Math.min(series.length - 1, idx)));
  }, [series.length]);

  if (series.length === 0) return <Empty description="暂无趋势数据" style={{ padding: 40 }} />;
  const hp = hover !== null ? series[hover] : null;

  const shapePath = (cx: number, cy: number, type: string) => {
    if (type === 'square') return `M${cx-3},${cy-3} L${cx+3},${cy-3} L${cx+3},${cy+3} L${cx-3},${cy+3} Z`;
    if (type === 'triangle') return `M${cx},${cy-4} L${cx+4},${cy+3} L${cx-4},${cy+3} Z`;
    if (type === 'diamond') return `M${cx},${cy-4} L${cx+4},${cy} L${cx},${cy+4} L${cx-4},${cy} Z`;
    return `M${cx-3.5},${cy} A3.5,3.5,0,1,1 ${cx+3.5},${cy} A3.5,3.5,0,1,1 ${cx-3.5},${cy} Z`;
  };

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}
        onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          {lines.map((l) => (
            <linearGradient key={l.key} id={`grad-${l.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={l.color} stopOpacity="0.18" />
              <stop offset="100%" stopColor={l.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={P.left} x2={W-P.right} y1={y(t)} y2={y(t)} stroke="#e4e7ec" strokeDasharray="4 4" />
            <text x={P.left-8} y={y(t)+4} textAnchor="end" fontSize="11" fill="#8a919f">{t}</text>
          </g>
        ))}
        {series.map((p, i) => (
          <text key={i} x={x(i)} y={H-10} textAnchor="middle" fontSize="10" fill="#8a919f">
            {(i === 0 || i === series.length-1 || i === Math.floor(series.length/2)) ? p.date.slice(5).replace('-','/') : ''}
          </text>
        ))}
        {lines.map((l) => (
          <g key={l.key}>
            <path d={`M${x(0).toFixed(1)},${y(0).toFixed(1)} ${series.map((p,i)=>`L${x(i).toFixed(1)},${y(p[l.key]).toFixed(1)}`).join(' ')} L${x(series.length-1).toFixed(1)},${(P.top+ch).toFixed(1)} Z`} fill={`url(#grad-${l.key})`} />
            <path d={l.path} fill="none" stroke={l.color} strokeWidth="2.6" strokeLinejoin="round" strokeLinecap="round" strokeDasharray={l.dash} />
            {series.map((p, i) => (
              <path key={i} d={shapePath(x(i), y(p[l.key]), l.shape)} fill="#fff" stroke={l.color} strokeWidth="2" />
            ))}
          </g>
        ))}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={P.top} y2={P.top+ch} stroke="#c9cdd4" strokeDasharray="3 3" />
            {lines.map((l) => (
              <path key={l.key} d={shapePath(x(hover), y(series[hover][l.key]), l.shape)} fill={l.color} stroke={l.color} strokeWidth="2" />
            ))}
          </g>
        )}
      </svg>
      {hp && hover !== null && (
        <div style={{ position:'absolute', left:`${(x(hover)/W)*100}%`, top:0, transform:'translateX(8px)', background:'#fff', border:'1px solid #e4e7ec', borderRadius:6, boxShadow:'0 4px 12px rgba(0,0,0,0.08)', padding:'8px 12px', fontSize:12, whiteSpace:'nowrap', zIndex:2, pointerEvents:'none' }}>
          <div style={{ fontWeight:600, marginBottom:6 }}>{hp.date}</div>
          {SERIES_META.map((m) => (
            <div key={m.key} style={{ display:'flex', alignItems:'center', gap:6, lineHeight:1.7 }}>
              <span style={{ width:8, height:8, borderRadius:2, background:m.color }} />
              <span style={{ color:'#8a919f' }}>{m.label}</span>
              <span style={{ marginLeft:'auto', fontWeight:600 }}>{hp[m.key]}</span>
            </div>
          ))}
        </div>
      )}
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
      const [s, t, ti] = await Promise.all([dashboardApi.summary(), dashboardApi.trend(30), dashboardApi.topIssues(5)]);
      setSummary(s); setTrend(t.series || []); setTopIssues(ti || []);
    } catch { /* 拦截器已提示 */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await runApi.trigger({ scope: 'all' });
      setTimeout(loadData, 1500);
    } catch { /* 拦截器已提示 */ }
    finally { setTriggering(false); }
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
      Message.success(state === 'resolved' ? '已标记为已处理' : state === 'ignored' ? '已忽略该异常' : '已恢复为待处理');
      loadData();
    } catch { /* 拦截器已提示 */ }
  };

  if (loading && !summary) return <div style={{ textAlign:'center', paddingTop:120 }}><Spin size={40} tip="加载巡检数据中..." /></div>;

  const total = summary?.total ?? 0;
  const normal = summary?.normal ?? 0;
  const rate = total > 0 ? normal / total : 0;
  const envCount = summary?.environments.length ?? 0;
  const worstEnvs = [...(summary?.environments ?? [])].sort((a, b) => {
    const ra = a.total > 0 ? a.normal / a.total : 0;
    const rb = b.total > 0 ? b.normal / b.total : 0;
    return ra - rb;
  });

  const conclusion = rate >= 0.9 ? '整体健康' : rate >= 0.6 ? '部分异常' : '需要立即处理';

  return (
    <div>
      <PageHeader title="总览" sub="平台整体巡检健康总览 · 近 30 天结果趋势"
        actions={<Button type="primary" icon={<IconRefresh />} loading={triggering} onClick={handleTrigger} size="large">立即巡检</Button>} />

      {/* 第 1 层：hero 结论 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <div className="panel-card" style={{ padding: 24, display: 'flex', alignItems: 'center', gap: 20, height: '100%' }}>
            <HealthDonut normal={normal} total={total} />
            <div>
              <div style={{ fontSize: 14, color: '#8a919f', marginBottom: 4 }}>整体健康状态</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: rate >= 0.9 ? '#16a34a' : rate >= 0.6 ? '#f59e0b' : '#dc2626' }}>{conclusion}</div>
              <div style={{ fontSize: 13, color: '#4b5563', marginTop: 8 }}>
                {envCount} 个环境 · {total} 项检查<br />
                正常 {normal} · 异常 {summary?.abnormal ?? 0} · 不可达 {summary?.unreachable ?? 0} · 失败 {summary?.failed ?? 0}
              </div>
            </div>
          </div>
        </Col>

        {/* 第 2 层：KPI 卡（CSS Grid 等宽等高） */}
        <Col xs={24} xl={16}>
          <div className="kpi-grid">
            {KPI_META.map((k) => {
              const val = summary ? summary[k.key] : 0;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0.0';
              const sub = k.key === 'total' ? '全部检查项' : `占总数 ${pct}%`;
              return (
                <div key={k.key} className="kpi-card" style={{ '--kpi-color': k.color } as CSSProperties}>
                  <div className="kpi-top"><span className="kpi-label">{k.label}</span><span className="kpi-icon">{k.icon}</span></div>
                  <div className="num kpi-value">{val}</div>
                  <div className="kpi-sub">{sub}</div>
                </div>
              );
            })}
          </div>
        </Col>
      </Row>

      {/* 第 3 层：趋势 + 环境对比 */}
      <Row className="dashboard-secondary-row" gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={16}>
          <div className="panel-card dashboard-secondary-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
              <div><div style={{ fontWeight: 600, fontSize: 15 }}>结果趋势</div><div className="sub-text" style={{ marginTop: 4 }}>近 30 天 · 线型+形状区分序列（可及性）</div></div>
              <div style={{ display: 'flex', gap: 14 }}>
                {SERIES_META.map((m) => (<span key={m.key} style={{ display:'flex', alignItems:'center', gap:5, fontSize:12, color:'#4e5969' }}><span style={{ width:9, height:9, borderRadius:2, background:m.color }} />{m.label}</span>))}
              </div>
            </div>
            <TrendChart series={trend} />
          </div>
        </Col>
        <Col xs={24} xl={8}>
          <div className="panel-card dashboard-secondary-card" style={{ padding: 20 }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 16 }}>环境健康对比（最差置顶）</div>
            {worstEnvs.length === 0 ? <Empty description="暂无环境" /> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {worstEnvs.map((e) => {
                  const er = e.total > 0 ? e.normal / e.total : 0;
                  const ec = er >= 0.9 ? '#16a34a' : er >= 0.6 ? '#f59e0b' : '#dc2626';
                  return (
                    <div key={e.environment_id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                        <span style={{ fontWeight: 500 }}>{e.name}</span>
                        <span style={{ fontWeight: 600, color: ec }}>{(er * 100).toFixed(1)}%</span>
                      </div>
                      <Progress percent={Math.round(er * 1000) / 10} size="small" showText={false} color={ec} />
                      <div className="sub-text" style={{ marginTop: 2 }}>正常 {e.normal} · 异常 {e.abnormal} · 不可达 {e.unreachable} · 失败 {e.failed}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Col>
      </Row>

      {/* 第 4 层：异常 Top 下钻 */}
      <div className="panel-card" style={{ marginTop: 16 }}>
        <div style={{ padding: '18px 20px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div><div style={{ fontWeight: 600, fontSize: 15 }}>巡检异常项</div><div className="sub-text" style={{ marginTop: 4 }}>最近一次巡检的异常/不可达/失败项，可逐项标记处置状态</div></div>
          <Button type="text" size="small" onClick={() => navigate('/results')}>查看全部结果 →</Button>
        </div>
        <Table
          rowKey={(r) => `${r.check_item_id}-${r.object_type}-${r.object_name}-${r.environment_id}`}
          data={topIssues}
          pagination={false}
          borderCell
          scroll={{ x: 1000 }}
          style={{ padding: '4px 8px 16px' }}
          noDataElement={<Empty description="最近一次巡检无异常，一切正常" style={{ padding: 32 }} />}
          columns={[
            { title: '处置', dataIndex: 'state', width: 90, resizable: true, render: (v: string) => v === 'resolved' ? <Tag color="green">已处理</Tag> : v === 'ignored' ? <Tag>已忽略</Tag> : <Tag color="red">待处理</Tag> },
            { title: '检查状态', dataIndex: 'status', width: 100, resizable: true, render: (v: string) => <StatusTag status={v as ResultStatus} /> },
            { title: '对象', dataIndex: 'object_name', render: (v: string, r: TopIssue) => <Typography.Text bold>{TARGET_TEXT[r.object_type] || r.object_type} · {v}</Typography.Text> },
            { title: '环境', dataIndex: 'environment_name', width: 110, resizable: true },
            { title: '判读', width: 220, resizable: true, ellipsis: true, render: (_: unknown, r: TopIssue) => { const e = parseEvidence(r.evidence); return <Tooltip position="top" content={<pre style={{ margin:0, whiteSpace:'pre-wrap' }}>{JSON.stringify(e, null, 2)}</pre>}><span style={{ color:'#4e5969', cursor:'help' }}>{e.detail || e.verdict || '-'}</span></Tooltip>; } },
            { title: '判定', width: 110, resizable: true, render: (_: unknown, r: TopIssue) => { const e = parseEvidence(r.evidence); return <Tag size="small" bordered>{(e.verdict && VERDICT_TEXT[e.verdict]) || e.verdict || '-'}</Tag>; } },
            { title: '操作', key: 'action', width: 200, fixed: 'right', render: (_: unknown, r: TopIssue) => (
              r.state === 'resolved'
                ? <Space>{<Tag color="green">已处理</Tag>}<Button key="reopen" type="text" size="small" onClick={() => handleTriage(r, 'pending')}>恢复待处理</Button></Space>
                : r.state === 'ignored'
                  ? <Button type="text" size="small" onClick={() => handleTriage(r, 'pending')}>恢复待处理</Button>
                  : <Space><Button type="text" size="small" status="success" onClick={() => handleTriage(r, 'resolved')}>标记已处理</Button><Button type="text" size="small" onClick={() => handleTriage(r, 'ignored')}>忽略</Button></Space>
            ) },
          ]}
        />
      </div>
    </div>
  );
}
