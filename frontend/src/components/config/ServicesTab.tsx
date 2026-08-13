import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Message,
  Popconfirm,
  Tag,
  Typography,
  Empty,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { envApi, nodeApi, serviceApi } from '../../api';
import type { Environment, PhysicalNode, SystemService, ServiceInput } from '../../types';

const { Text } = Typography;
const FormItem = Form.Item;

export default function ServicesTab() {
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [envId, setEnvId] = useState<number | undefined>();
  const [nodes, setNodes] = useState<PhysicalNode[]>([]);
  const [services, setServices] = useState<SystemService[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [visible, setVisible] = useState(false);
  const [form] = Form.useForm<ServiceInput>();

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

  const loadNodes = useCallback(async () => {
    if (envId === undefined) return;
    try {
      const resp = await nodeApi.list(envId, { page: 1, page_size: 100 });
      setNodes(resp.items);
    } catch {
      /* 拦截器已提示 */
    }
  }, [envId]);

  const loadServices = useCallback(
    async (p: number) => {
      if (envId === undefined) return;
      setLoading(true);
      try {
        const resp = await serviceApi.list(envId, { page: p, page_size: 10 });
        setServices(resp.items);
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
    loadNodes();
    setPage(1);
    loadServices(1);
  }, [envId, loadNodes, loadServices]);

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({ enabled: true });
    setVisible(true);
  };

  const handleSubmit = async () => {
    if (envId === undefined) return;
    const values = await form.validate();
    try {
      await serviceApi.create(envId, values);
      Message.success('系统服务已添加');
      setVisible(false);
      loadServices(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const handleDelete = async (serviceId: number) => {
    if (envId === undefined) return;
    try {
      await serviceApi.remove(envId, serviceId);
      Message.success('系统服务已删除');
      loadServices(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const nodeName = (nodeId: number | null) => {
    const n = nodes.find((x) => x.id === nodeId);
    return n ? `${n.hostname} (${n.ip})` : '-';
  };

  const currentEnv = envs.find((e) => e.id === envId);

  const columns: TableColumnProps<SystemService>[] = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    {
      title: '服务名',
      dataIndex: 'name',
      render: (v: string) => <Text bold>{v}</Text>,
    },
    { title: '端口', dataIndex: 'port', width: 90, render: (v: number | null) => v ?? '-' },
    { title: '所在节点', dataIndex: 'node_id', render: (v: number | null) => nodeName(v) },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 90,
      resizable: true,
      render: (v: boolean) => <Tag color={v ? 'green' : 'gray'}>{v ? '启用' : '停用'}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      resizable: true,
      render: (_: unknown, record: SystemService) => (
        <Popconfirm title="确认删除该系统服务？" onOk={() => handleDelete(record.id)}>
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
            <div style={{ fontWeight: 600, fontSize: 15 }}>系统服务管理</div>
            <div className="sub-text" style={{ marginTop: 4 }}>mysql / nginx / keepalived / haproxy 等长期服务</div>
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
          新建服务
        </Button>
      </div>

      {envId === undefined ? (
        <Empty description="请先选择环境" style={{ padding: 40 }} />
      ) : (
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          data={services}
          borderCell
          pagination={{
            current: page,
            pageSize: 10,
            total,
            showTotal: true,
            onChange: setPage,
          }}
          noDataElement={<Empty description={`环境 ${currentEnv?.name ?? ""} 暂无系统服务`} />}
        />
      )}

      <Modal
        title={`新建系统服务 · ${currentEnv?.name ?? ''}`}
        visible={visible}
        onCancel={() => setVisible(false)}
        onOk={handleSubmit}
        unmountOnExit
      >
        <Form form={form} layout="vertical">
          <FormItem label="服务名" field="name" rules={[{ required: true, message: '请输入服务名' }]}>
            <Input placeholder="如 mysql / nginx / keepalived / haproxy" />
          </FormItem>
          <FormItem label="端口" field="port">
            <InputNumber placeholder="可选，如 3306" style={{ width: '100%' }} />
          </FormItem>
          <FormItem label="所在节点" field="node_id">
            <Select placeholder="选择节点（可选）" allowClear>
              {nodes.map((n) => (
                <Select.Option key={n.id} value={n.id}>
                  {n.hostname} ({n.ip})
                </Select.Option>
              ))}
            </Select>
          </FormItem>
          <FormItem label="是否启用" field="enabled">
            <Switch checkedText="启用" uncheckedText="停用" />
          </FormItem>
        </Form>
      </Modal>
    </div>
  );
}
