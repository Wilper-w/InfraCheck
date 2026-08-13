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
  Space,
  Message,
  Popconfirm,
  Typography,
  Empty,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { nodeApi, serviceApi } from '../../api';
import { useCrudTable } from '../../hooks/useCrudTable';
import { useEnvironments } from '../../hooks/useEnvironments';
import { PROBE_MODE_TEXT } from '../../constants';
import type { PhysicalNode, SystemService, ServiceInput, ProbeMode } from '../../types';

const { Text } = Typography;
const FormItem = Form.Item;

const PROBE_HINT: Record<ProbeMode, string> = {
  systemd: '执行 systemctl is-active <服务名>，适用于标准 systemd 托管服务',
  port: '检查端口监听（ss -ltn），能证明服务真正对外提供能力',
  vip: '检查虚拟 IP 是否绑定在本机 —— keepalived 进程活着但 VIP 不在本机同样是异常',
};

export default function ServicesTab() {
  const { envs, envId, setEnvId, currentEnv } = useEnvironments();
  const [nodes, setNodes] = useState<PhysicalNode[]>([]);

  const crud = useCrudTable<SystemService, ServiceInput>({
    api: {
      list: (params) => serviceApi.list(envId!, params),
      create: (data) => serviceApi.create(envId!, data),
      update: (id, data) => serviceApi.update(envId!, id, data),
      remove: (serviceId) => serviceApi.remove(envId!, serviceId),
    },
    labels: { created: '系统服务已添加', updated: '系统服务已更新', deleted: '系统服务已删除' },
    ready: envId !== undefined,
    resetKey: envId,
    createDefaults: { enabled: true, probe_mode: 'systemd' },
    toFormValues: (r) => ({
      name: r.name,
      node_id: r.node_id,
      port: r.port,
      enabled: r.enabled,
      probe_mode: r.probe_mode,
      probe_target: r.probe_target,
    }),
  });

  // 探测方式决定端口 / VIP 哪个字段成为必填
  const probeMode = (Form.useWatch('probe_mode', crud.form) as ProbeMode) || 'systemd';

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

  const handleToggle = async (record: SystemService) => {
    try {
      await serviceApi.toggle(envId!, record.id);
      Message.success(record.enabled ? '已停用，该服务不再进入巡检' : '已启用，该服务将纳入巡检');
      await crud.reload();
    } catch {
      /* 拦截器已提示 */
    }
  };

  const nodeName = (nodeId: number | null) => {
    const n = nodes.find((x) => x.id === nodeId);
    return n ? `${n.hostname} (${n.ip})` : '-';
  };

  const columns: TableColumnProps<SystemService>[] = [
    { title: 'ID', dataIndex: 'id', width: 64 },
    {
      title: '服务名',
      dataIndex: 'name',
      render: (v: string) => <Text bold>{v}</Text>,
    },
    {
      title: '探测方式',
      dataIndex: 'probe_mode',
      width: 200,
      render: (v: ProbeMode, r: SystemService) => (
        <Space size={6}>
          <span className="meta-tag">{PROBE_MODE_TEXT[v] || v}</span>
          <span className="sub-text">
            {v === 'port' ? `:${r.port ?? '-'}` : v === 'vip' ? r.probe_target || '-' : r.name}
          </span>
        </Space>
      ),
    },
    { title: '所在节点', dataIndex: 'node_id', render: (v: number | null) => nodeName(v) },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 80,
      render: (v: boolean, record: SystemService) => (
        <Switch checked={v} size="small" onChange={() => handleToggle(record)} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 128,
      render: (_: unknown, record: SystemService) => (
        <Space size={2}>
          <Button type="text" size="small" onClick={() => crud.openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该系统服务？" onOk={() => crud.remove(record.id)}>
            <Button type="text" size="small" status="danger">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--s-4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-4)' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 'var(--fs-md)' }}>系统服务管理</div>
            <div className="sub-text" style={{ marginTop: 2 }}>
              停用的服务不进入巡检范围
            </div>
          </div>
          <Select
            placeholder="选择环境"
            style={{ width: 176 }}
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
          pagination={crud.pagination}
          noDataElement={<Empty description={`环境 ${currentEnv?.name ?? ''} 暂无系统服务`} />}
        />
      )}

      <Modal
        title={`${crud.editing ? '编辑' : '新建'}系统服务 · ${currentEnv?.name ?? ''}`}
        visible={crud.visible}
        onCancel={() => crud.setVisible(false)}
        onOk={crud.submit}
        unmountOnExit
      >
        <Form form={crud.form} layout="vertical">
          <FormItem label="服务名" field="name" rules={[{ required: true, message: '请输入服务名' }]}>
            <Input placeholder="如 mysql / nginx / keepalived / haproxy" />
          </FormItem>

          <FormItem
            label="探测方式"
            field="probe_mode"
            rules={[{ required: true, message: '请选择探测方式' }]}
            extra={<span className="sub-text">{PROBE_HINT[probeMode]}</span>}
          >
            <Select>
              <Select.Option value="systemd">systemd 单元状态</Select.Option>
              <Select.Option value="port">端口监听</Select.Option>
              <Select.Option value="vip">VIP 绑定</Select.Option>
            </Select>
          </FormItem>

          {probeMode === 'vip' ? (
            <FormItem label="虚拟 IP" field="probe_target" rules={[{ required: true, message: '请输入 VIP 地址' }]}>
              <Input placeholder="如 10.0.1.250" />
            </FormItem>
          ) : (
            <FormItem
              label={probeMode === 'port' ? '端口（探测依据）' : '端口（仅登记）'}
              field="port"
              rules={probeMode === 'port' ? [{ required: true, message: '端口探测必须填写端口' }] : []}
            >
              <InputNumber placeholder="如 3306" style={{ width: '100%' }} min={1} max={65535} />
            </FormItem>
          )}

          <FormItem label="所在节点" field="node_id">
            <Select placeholder="选择节点（可选）" allowClear>
              {nodes.map((n) => (
                <Select.Option key={n.id} value={n.id}>
                  {n.hostname} ({n.ip})
                </Select.Option>
              ))}
            </Select>
          </FormItem>

          <FormItem label="纳入巡检" field="enabled" triggerPropName="checked">
            <Switch checkedText="启用" uncheckedText="停用" />
          </FormItem>
        </Form>
      </Modal>
    </div>
  );
}
