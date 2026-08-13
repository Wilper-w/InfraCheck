import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Message,
  Popconfirm,
  Tag,
  Typography,
  Empty,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { envApi, nodeApi } from '../../api';
import type { Environment, PhysicalNode, NodeInput } from '../../types';

const { Text } = Typography;
const FormItem = Form.Item;

export default function NodesTab() {
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [envId, setEnvId] = useState<number | undefined>();
  const [nodes, setNodes] = useState<PhysicalNode[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [visible, setVisible] = useState(false);
  const [form] = Form.useForm<NodeInput>();

  const loadEnvs = useCallback(async () => {
    try {
      const resp = await envApi.list({ page: 1, page_size: 100 });
      setEnvs(resp.items);
      if (!envId && resp.items.length > 0) setEnvId(resp.items[0].id);
    } catch {
      /* 拦截器已提示 */
    }
  }, [envId]);

  useEffect(() => {
    loadEnvs();
  }, [loadEnvs]);

  const loadNodes = useCallback(
    async (p: number) => {
      if (envId === undefined) return;
      setLoading(true);
      try {
        const resp = await nodeApi.list(envId, { page: p, page_size: 10 });
        setNodes(resp.items);
        setTotal(resp.total);
      } catch {
        /* 拦截器已提示 */
      } finally {
        setLoading(false);
      }
    },
    [envId],
  );

  useEffect(() => {
    setPage(1);
    loadNodes(1);
  }, [envId, loadNodes]);

  const openCreate = () => {
    form.resetFields();
    setVisible(true);
  };

  const handleSubmit = async () => {
    if (envId === undefined) return;
    const values = await form.validate();
    try {
      await nodeApi.create(envId, values);
      Message.success('物理机已添加');
      setVisible(false);
      loadNodes(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const handleDelete = async (nodeId: number) => {
    if (envId === undefined) return;
    try {
      await nodeApi.remove(envId, nodeId);
      Message.success('物理机已删除');
      loadNodes(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const currentEnv = envs.find((e) => e.id === envId);

  const columns: TableColumnProps<PhysicalNode>[] = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '主机名', dataIndex: 'hostname', render: (v: string) => <Text bold>{v}</Text> },
    { title: 'IP 地址', dataIndex: 'ip', width: 150 },
    {
      title: '操作系统',
      dataIndex: 'os_flavor',
      width: 130,
      resizable: true,
      render: (v: string | null) => (v ? <Tag color={v === 'centos' ? 'orangered' : 'arcoblue'}>{v}</Tag> : <Tag>继承环境</Tag>),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      resizable: true,
      render: (v: string) => new Date(v).toLocaleString('zh-CN', { hour12: false }),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      resizable: true,
      render: (_: unknown, record: PhysicalNode) => (
        <Popconfirm title="确认删除该物理机？" onOk={() => handleDelete(record.id)}>
          <Button type="text" size="small" status="danger">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>物理机管理</div>
            <div className="sub-text" style={{ marginTop: 4 }}>当前环境下的物理机清单（SSH 巡检对象）</div>
          </div>
          <Select
            placeholder="选择环境"
            style={{ width: 180 }}
            value={envId}
            onChange={(v) => setEnvId(Number(v))}
          >
            {envs.map((e) => (
              <Select.Option key={e.id} value={e.id}>
                {e.name}
              </Select.Option>
            ))}
          </Select>
        </div>
        <Button type="primary" disabled={envId === undefined} icon={<IconPlus />} onClick={openCreate}>
          新建物理机
        </Button>
      </div>

      {envId === undefined ? (
        <Empty description="请先选择环境" style={{ padding: 40 }} />
      ) : (
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          data={nodes}
          borderCell
          pagination={{
            current: page,
            pageSize: 10,
            total,
            showTotal: true,
            onChange: setPage,
          }}
          noDataElement={<Empty description={`环境 ${currentEnv?.name ?? ''} 暂无物理机`} />}
        />
      )}

      <Modal
        title={`新建物理机 · ${currentEnv?.name ?? ''}`}
        visible={visible}
        onCancel={() => setVisible(false)}
        onOk={handleSubmit}
        unmountOnExit
      >
        <Form form={form} layout="vertical">
          <FormItem label="主机名" field="hostname" rules={[{ required: true, message: '请输入主机名' }]}>
            <Input placeholder="如 node-env-01-1" />
          </FormItem>
          <FormItem label="IP 地址" field="ip" rules={[{ required: true, message: '请输入 IP' }]}>
            <Input placeholder="如 10.0.1.1" />
          </FormItem>
          <FormItem label="操作系统（留空继承环境）" field="os_flavor">
            <Select allowClear placeholder="继承环境">
              <Select.Option value="ubuntu">Ubuntu</Select.Option>
              <Select.Option value="centos">CentOS</Select.Option>
            </Select>
          </FormItem>
        </Form>
      </Modal>
    </div>
  );
}
