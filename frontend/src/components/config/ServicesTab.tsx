import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Popconfirm,
  Tag,
  Typography,
  Empty,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { nodeApi, serviceApi } from '../../api';
import { useCrudTable } from '../../hooks/useCrudTable';
import { useEnvironments } from '../../hooks/useEnvironments';
import type { PhysicalNode, SystemService, ServiceInput } from '../../types';

const { Text } = Typography;
const FormItem = Form.Item;

export default function ServicesTab() {
  const { envs, envId, setEnvId, currentEnv } = useEnvironments();
  const [nodes, setNodes] = useState<PhysicalNode[]>([]);

  const crud = useCrudTable<SystemService, ServiceInput>({
    api: {
      list: (params) => serviceApi.list(envId!, params),
      create: (data) => serviceApi.create(envId!, data),
      remove: (serviceId) => serviceApi.remove(envId!, serviceId),
    },
    labels: { created: '系统服务已添加', deleted: '系统服务已删除' },
    ready: envId !== undefined,
    resetKey: envId,
    createDefaults: { enabled: true },
  });

  // 供表单下拉与表格「所在节点」列使用
  useEffect(() => {
    if (envId === undefined) return;
    void (async () => {
      try {
        const resp = await nodeApi.list(envId, { page: 1, page_size: 100 });
        setNodes(resp.items);
      } catch {
        /* 拦截器已提示 */
      }
    })();
  }, [envId]);

  const nodeName = (nodeId: number | null) => {
    const n = nodes.find((x) => x.id === nodeId);
    return n ? `${n.hostname} (${n.ip})` : '-';
  };

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
        <Popconfirm title="确认删除该系统服务？" onOk={() => crud.remove(record.id)}>
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
        <Button type="primary" disabled={envId === undefined} icon={<IconPlus />} onClick={crud.openCreate}>
          新建服务
        </Button>
      </div>

      {envId === undefined ? (
        <Empty description="请先选择环境" style={{ padding: 40 }} />
      ) : (
        <Table
          rowKey="id"
          loading={crud.loading}
          columns={columns}
          data={crud.items}
          borderCell
          pagination={crud.pagination}
          noDataElement={<Empty description={`环境 ${currentEnv?.name ?? ''} 暂无系统服务`} />}
        />
      )}

      <Modal
        title={`新建系统服务 · ${currentEnv?.name ?? ''}`}
        visible={crud.visible}
        onCancel={() => crud.setVisible(false)}
        onOk={crud.submit}
        unmountOnExit
      >
        <Form form={crud.form} layout="vertical">
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
