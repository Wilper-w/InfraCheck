import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Tag,
  Select,
  Empty,
  Typography,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconSearch } from '@arco-design/web-react/icon';
import PageHeader from '../components/PageHeader';
import { auditApi } from '../api';
import type { AuditLog } from '../types';

const { Text } = Typography;

const ACTION_META: Record<string, { color: string; text: string }> = {
  'run.trigger': { color: 'arcoblue', text: '触发巡检' },
  'report.generate': { color: 'green', text: '生成报告' },
  'environment.create': { color: 'purple', text: '创建环境' },
  'environment.update': { color: 'purple', text: '更新环境' },
  'environment.delete': { color: 'red', text: '删除环境' },
  'node.create': { color: 'purple', text: '新增物理机' },
  'node.delete': { color: 'red', text: '删除物理机' },
  'service.create': { color: 'purple', text: '新增服务' },
  'service.delete': { color: 'red', text: '删除服务' },
  'check_item.create': { color: 'purple', text: '新建巡检项' },
  'check_item.update': { color: 'purple', text: '更新巡检项' },
  'check_item.delete': { color: 'red', text: '删除巡检项' },
  'check_item.toggle': { color: 'orange', text: '切换巡检项' },
};

const fmtTime = (s: string) => new Date(s).toLocaleString('zh-CN', { hour12: false });

export default function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [loading, setLoading] = useState(true);
  const [actor, setActor] = useState<string | undefined>();
  const [actors, setActors] = useState<string[]>([]);

  const load = useCallback(
    async (p: number, size: number) => {
      setLoading(true);
      try {
        const resp = await auditApi.list({ page: p, page_size: size, ...(actor ? { actor } : {}) });
        setLogs(resp.items);
        setTotal(resp.total);
        setActors((prev) => Array.from(new Set([...prev, ...resp.items.map((x) => x.actor)])));
      } catch {
        /* 拦截器已提示 */
      } finally {
        setLoading(false);
      }
    },
    [actor],
  );

  useEffect(() => {
    setPage(1);
    load(1, pageSize);
  }, [actor, pageSize, load]);

  const columns: TableColumnProps<AuditLog>[] = [
    {
      title: '操作人',
      dataIndex: 'actor',
      width: 140,
      resizable: true,
      render: (v: string) => (
        <Text bold>
          <Tag color="arcoblue" size="small" style={{ marginRight: 4 }}>
            {v ? v[0]?.toUpperCase() : '?'}
          </Tag>
          {v}
        </Text>
      ),
    },
    {
      title: '动作',
      dataIndex: 'action',
      width: 150,
      resizable: true,
      render: (v: string) => {
        const m = ACTION_META[v] ?? { color: 'gray', text: v };
        return <Tag color={m.color}>{m.text}</Tag>;
      },
    },
    { title: '目标', dataIndex: 'target_ref', width: 130, render: (v: string | null) => v || '-' },
    { title: '详情', dataIndex: 'detail' },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => <span className="table-time">{fmtTime(v)}</span>,
    },
  ];

  return (
    <div>
      <PageHeader title="审计日志" sub="谁在何时做了什么的可追溯记录（巡检触发、报告生成、配置变更）" />
      <div className="panel-card">
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
          <Select
            placeholder="按操作人筛选"
            allowClear
            value={actor}
            onChange={(v) => setActor(v as string | undefined)}
            prefix={<IconSearch />}
            style={{ width: 200 }}
          >
            {actors.map((a) => (
              <Select.Option key={a} value={a}>
                {a}
              </Select.Option>
            ))}
          </Select>
        </div>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          data={logs}
          scroll={{ x: 900 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showTotal: true,
            sizeCanChange: true,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              if (nextPageSize !== pageSize) {
                setPageSize(nextPageSize);
              } else {
                load(nextPage, nextPageSize);
              }
            },
          }}
          noDataElement={<Empty description="暂无审计记录" />}
        />
      </div>
    </div>
  );
}
