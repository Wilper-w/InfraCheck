import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Drawer,
  Descriptions,
  Typography,
  Select,
  Empty,
  Spin,
  Tooltip,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import PageHeader from '../components/PageHeader';
import StatusTag, { RunStatusTag } from '../components/StatusTag';
import { runApi } from '../api';
import type { Run, RunDetail, CheckResult, ResultStatus } from '../types';
import { VERDICT_TEXT } from '../constants';

const { Text } = Typography;

const fmtTime = (s: string | null) => (s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '-');
const TRIGGER_META: Record<string, { color: string; text: string }> = {
  manual: { color: 'arcoblue', text: '手动' },
  scheduled: { color: 'purple', text: '定时' },
};
const TARGET_TEXT: Record<string, string> = {
  physical: '物理机',
  service: '系统服务',
  cluster: '集群',
  pod: 'Pod',
};

function runTotal(r: RunDetail['results']) {
  if (!r) return 0;
  return (r.normal || 0) + (r.abnormal || 0) + (r.unreachable || 0) + (r.failed || 0);
}

function parseEvidence(raw: string): { verdict?: string; detail?: string; output?: string } {
  try {
    return JSON.parse(raw);
  } catch {
    return { detail: raw };
  }
}

export default function Results() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const [detailRun, setDetailRun] = useState<RunDetail | null>(null);
  const [results, setResults] = useState<CheckResult[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<ResultStatus | undefined>();
  const [resultsPage, setResultsPage] = useState(1);
  const [resultsPageSize, setResultsPageSize] = useState(20);
  const [resultsTotal, setResultsTotal] = useState(0);

  const loadRuns = useCallback(async (p: number, size: number) => {
    setLoading(true);
    try {
      const resp = await runApi.list({ page: p, page_size: size });
      setRuns(resp.items);
      setTotal(resp.total);
    } catch {
      /* 拦截器已提示 */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns(page, pageSize);
  }, [page, pageSize, loadRuns]);

  const loadResults = useCallback(
    async (runId: number, p: number, size: number, status?: ResultStatus) => {
      setResultsLoading(true);
      try {
        const resp = await runApi.results(runId, {
          page: p,
          page_size: size,
          ...(status ? { status } : {}),
        });
        setResults(resp.items);
        setResultsTotal(resp.total);
      } catch {
        /* 拦截器已提示 */
      } finally {
        setResultsLoading(false);
      }
    },
    [],
  );

  const openDetail = useCallback(
    async (run: Run) => {
      const detail = await runApi.detail(run.id);
      setDetailRun(detail);
      setStatusFilter(undefined);
      setResultsPage(1);
      loadResults(run.id, 1, resultsPageSize);
    },
    [loadResults, resultsPageSize],
  );

  const runColumns: TableColumnProps<Run>[] = [
    {
      title: '巡检编号',
      dataIndex: 'id',
      width: 100,
      resizable: true,
      render: (v: number) => <Text bold>#{v}</Text>,
    },
    {
      title: '触发方式',
      dataIndex: 'trigger',
      width: 110,
      resizable: true,
      render: (v: string) => (
        <span className="meta-tag">{TRIGGER_META[v]?.text ?? v}</span>
      ),
    },
    { title: '触发人', dataIndex: 'triggered_by', width: 130 },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      width: 170,
      render: (v: string) => <span className="table-time">{fmtTime(v)}</span>,
    },
    {
      title: '结束时间',
      dataIndex: 'finished_at',
      width: 170,
      render: (v: string | null) => <span className="table-time">{fmtTime(v)}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      resizable: true,
      render: (v: string) => <RunStatusTag status={v} />,
    },
    {
      title: '操作',
      key: 'action',
      width: 130,
      resizable: true,
      render: (_: unknown, record: Run) => (
        <Button type="text" size="small" onClick={() => openDetail(record)}>
          查看明细
        </Button>
      ),
    },
  ];

  const resultColumns: TableColumnProps<CheckResult>[] = [
    { title: '对象类型', dataIndex: 'object_type', width: 90, render: (v: string) => TARGET_TEXT[v] || v },
    { title: '对象', dataIndex: 'object_name', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      resizable: true,
      render: (v: ResultStatus) => <StatusTag status={v} />,
    },
    {
      title: '判读结果',
      width: 220,
      resizable: true,
      ellipsis: true,
      render: (_: unknown, r: CheckResult) => {
        const e = parseEvidence(r.evidence);
        return (
          <Tooltip position="top" content={<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(e, null, 2)}</pre>}>
            <span style={{ color: 'var(--c-text-2)', cursor: 'help' }}>{e.detail || e.verdict || '-'}</span>
          </Tooltip>
        );
      },
    },
    {
      title: '证据判定',
      key: 'evidence',
      width: 130,
      resizable: true,
      render: (_: unknown, r: CheckResult) => {
        const e = parseEvidence(r.evidence);
        const text = (e.verdict && VERDICT_TEXT[e.verdict]) || e.verdict || '-';
        return (
          <Tooltip position="top" content={<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(e, null, 2)}</pre>}>
            <span className="meta-tag" style={{ cursor: 'help' }}>
              {text}
            </span>
          </Tooltip>
        );
      },
    },
  ];

  return (
    <div>
      <PageHeader title="巡检结果" sub="历次巡检记录与逐项检查结果，点击可查看明细与原始证据" />

      <div className="panel-card">
        <Table
          rowKey="id"
          loading={loading}
          columns={runColumns}
          data={runs}
          scroll={{ x: 920 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showTotal: true,
            sizeCanChange: true,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              setPageSize(nextPageSize);
            },
          }}
          noDataElement={
            <Empty description="暂无巡检记录，请先触发一次巡检" />
          }
        />
      </div>

      <Drawer
        width={900}
        title={detailRun ? `巡检 #${detailRun.id} 明细` : '巡检明细'}
        visible={!!detailRun}
        onCancel={() => setDetailRun(null)}
        footer={null}
        unmountOnExit
        className="result-pane"
      >
        {detailRun && (
          <>
            <Descriptions
              column={3}
              colon="："
              border
              title="基本信息"
              data={[
                { label: '触发方式', value: TRIGGER_META[detailRun.trigger]?.text ?? detailRun.trigger },
                { label: '触发人', value: detailRun.triggered_by },
                { label: '开始时间', value: fmtTime(detailRun.started_at) },
                { label: '结束时间', value: fmtTime(detailRun.finished_at) },
                { label: '状态', value: detailRun.status === 'finished' ? '已完成' : detailRun.status === 'running' ? '运行中' : '失败' },
                {
                  label: '总结',
                  value: detailRun.results
                    ? `共 ${runTotal(detailRun.results)} 项：正常 ${detailRun.results.normal ?? 0} · 异常 ${detailRun.results.abnormal ?? 0} · 不可达 ${detailRun.results.unreachable ?? 0} · 失败 ${detailRun.results.failed ?? 0}`
                    : '-',
                },
              ]}
              style={{ marginBottom: 20 }}
            />

            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12 }}>
              <span style={{ fontWeight: 600 }}>检查结果</span>
              <Select
                placeholder="按状态筛选"
                allowClear
                value={statusFilter}
                onChange={(v) => {
                  setStatusFilter(v as ResultStatus | undefined);
                  setResultsPage(1);
                  loadResults(detailRun.id, 1, resultsPageSize, v as ResultStatus | undefined);
                }}
                style={{ width: 160 }}
              >
                <Select.Option value="normal">正常</Select.Option>
                <Select.Option value="abnormal">异常</Select.Option>
                <Select.Option value="unreachable">不可达</Select.Option>
                <Select.Option value="failed">检查失败</Select.Option>
              </Select>
              <Text type="secondary">共 {resultsTotal} 条</Text>
            </div>

            {resultsLoading ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin />
              </div>
            ) : (
              <Table
                rowKey="id"
                columns={resultColumns}
                data={results}
                scroll={{ x: 900 }}
                expandedRowRender={(r: CheckResult) => {
                  const e = parseEvidence(r.evidence);
                  return (
                    <pre
                      style={{
                        margin: 0,
                        fontSize: 12,
                        lineHeight: 1.6,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                        color: 'var(--c-text-2)',
                      }}
                    >
                      {JSON.stringify(e, null, 2)}
                    </pre>
                  );
                }}
                pagination={{
                  current: resultsPage,
                  pageSize: resultsPageSize,
                  total: resultsTotal,
                  showTotal: true,
                  sizeCanChange: true,
                  onChange: (nextPage, nextPageSize) => {
                    setResultsPage(nextPage);
                    setResultsPageSize(nextPageSize);
                    loadResults(detailRun.id, nextPage, nextPageSize, statusFilter);
                  },
                }}
                noDataElement={<Empty description="无符合条件的结果" />}
              />
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}
