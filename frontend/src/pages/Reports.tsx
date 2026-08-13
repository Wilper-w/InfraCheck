import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Modal,
  Typography,
  Space,
  Tag,
  Empty,
  Message,
  Spin,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconEye, IconDownload, IconFile } from '@arco-design/web-react/icon';
import PageHeader from '../components/PageHeader';
import { reportApi } from '../api';
import type { Report } from '../types';

const { Text } = Typography;

const fmtTime = (s: string) => new Date(s).toLocaleString('zh-CN', { hour12: false });

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // 预览
  const [previewId, setPreviewId] = useState<number | null>(null);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const resp = await reportApi.list({ page: p, page_size: 10 });
      setReports(resp.items);
      setTotal(resp.total);
    } catch {
      /* 拦截器已提示 */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(page);
  }, [page, load]);

  const openPreview = async (id: number) => {
    setPreviewId(id);
    setPreviewHtml('');
    setPreviewLoading(true);
    try {
      const html = await reportApi.fetchHtml(id);
      setPreviewHtml(html);
    } catch {
      /* 拦截器已提示 */
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleExport = async (record: Report, kind: 'html' | 'markdown') => {
    try {
      const ext = kind === 'html' ? 'html' : 'md';
      await reportApi.download(record.id, kind, `infracheck-report-run${record.run_id}.${ext}`);
      Message.success(`已导出 ${ext.toUpperCase()} 报告`);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const columns: TableColumnProps<Report>[] = [
    {
      title: '报告编号',
      dataIndex: 'id',
      width: 110,
      resizable: true,
      render: (v: number) => <Text bold>#{v}</Text>,
    },
    { title: '对应巡检', dataIndex: 'run_id', width: 110, render: (v: number) => <Tag color="arcoblue">run #{v}</Tag> },
    { title: '生成人', dataIndex: 'rendered_by', width: 130 },
    { title: '生成时间', dataIndex: 'generated_at', render: (v: string) => fmtTime(v) },
    {
      title: '格式',
      key: 'formats',
      width: 180,
      resizable: true,
      render: () => (
        <Space size={4}>
          <Tag color="green">HTML</Tag>
          <Tag color="orange">Markdown</Tag>
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Report) => (
        <Space>
          <Button size="small" icon={<IconEye />} onClick={() => openPreview(record.id)}>
            预览
          </Button>
          <Button size="small" type="secondary" icon={<IconDownload />} onClick={() => handleExport(record, 'html')}>
            导出 HTML
          </Button>
          <Button size="small" type="secondary" icon={<IconFile />} onClick={() => handleExport(record, 'markdown')}>
            导出 MD
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="报告归档"
        sub="每次巡检自动生成 HTML / Markdown 双格式报告，可预览与导出归档"
      />

      <div className="panel-card">
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          data={reports}
          pagination={{
            current: page,
            pageSize: 10,
            total,
            showTotal: true,
            onChange: setPage,
          }}
          noDataElement={<Empty description="暂无报告，触发巡检后自动生成" />}
        />
      </div>

      <Modal
        title={previewId ? `巡检报告 #${previewId} 预览` : '报告预览'}
        visible={previewId !== null}
        onCancel={() => setPreviewId(null)}
        footer={null}
        style={{ width: 860 }}
        unmountOnExit
        className="report-modal"
      >
        <div style={{ height: '70vh' }}>
          {previewLoading ? (
            <div style={{ textAlign: 'center', paddingTop: 80 }}>
              <Spin size={40} tip="加载报告..." />
            </div>
          ) : (
            <iframe
              title="report-preview"
              srcDoc={previewHtml}
              style={{ width: '100%', height: '100%', border: '1px solid var(--c-border)', borderRadius: 6 }}
            />
          )}
        </div>
      </Modal>
    </div>
  );
}
