import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Space,
  Message,
  Popconfirm,
  Tag,
  Typography,
  Empty,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { checkItemApi } from '../../api';
import type { CheckItem, CheckItemInput } from '../../types';
import { TARGET_TYPE_TEXT } from '../../constants';

const { Text } = Typography;
const FormItem = Form.Item;

export default function CheckItemsTab() {
  const [list, setList] = useState<CheckItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(false);
  const [editing, setEditing] = useState<CheckItem | null>(null);
  const [form] = Form.useForm<CheckItemInput>();

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const resp = await checkItemApi.list({ page: p, page_size: 10 });
      setList(resp.items);
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

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setVisible(true);
  };

  const openEdit = (record: CheckItem) => {
    setEditing(record);
    form.setFieldsValue({
      name: record.name,
      target_type: record.target_type,
      os_flavor: record.os_flavor,
      description: record.description,
      config: record.config,
    });
    setVisible(true);
  };

  const handleSubmit = async () => {
    const values = await form.validate();
    try {
      if (editing) {
        await checkItemApi.update(editing.id, values);
        Message.success('巡检项已更新');
      } else {
        await checkItemApi.create(values);
        Message.success('巡检项已创建');
      }
      setVisible(false);
      load(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await checkItemApi.remove(id);
      Message.success('巡检项已删除');
      load(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const handleToggle = async (record: CheckItem) => {
    try {
      await checkItemApi.toggle(record.id);
      Message.success(record.enabled ? '已停用该巡检项' : '已启用该巡检项');
      load(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const columns: TableColumnProps<CheckItem>[] = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '名称', dataIndex: 'name', render: (v: string) => <Text bold>{v}</Text> },
    {
      title: '对象类型',
      dataIndex: 'target_type',
      width: 110,
      resizable: true,
      render: (v: string) => (
        <Tag color={v === 'service' ? 'purple' : v === 'cluster' ? 'cyan' : 'arcoblue'}>
          {TARGET_TYPE_TEXT[v] || v}
        </Tag>
      ),
    },
    {
      title: '操作系统',
      dataIndex: 'os_flavor',
      width: 110,
      resizable: true,
      render: (v: string | null) => (v ? <Tag>{v}</Tag> : <Tag color="gray">全部</Tag>),
    },
    { title: '描述', dataIndex: 'description', render: (v: string) => v || '-' },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 90,
      resizable: true,
      render: (v: boolean, record: CheckItem) => (
        <Switch checked={v} onChange={() => handleToggle(record)} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      resizable: true,
      render: (_: unknown, record: CheckItem) => (
        <Space>
          <Button type="text" size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该巡检项？" onOk={() => handleDelete(record.id)}>
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>巡检项管理</div>
          <div className="sub-text" style={{ marginTop: 4 }}>按对象类型 + 操作系统发行版编排的检查定义</div>
        </div>
        <Button type="primary" icon={<IconPlus />} onClick={openCreate}>
          新建巡检项
        </Button>
      </div>

      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        data={list}
        borderCell
        pagination={{
          current: page,
          pageSize: 10,
          total,
          showTotal: true,
          onChange: setPage,
        }}
        noDataElement={<Empty description="暂无巡检项" />}
      />

      <Modal
        title={editing ? '编辑巡检项' : '新建巡检项'}
        visible={visible}
        onCancel={() => setVisible(false)}
        onOk={handleSubmit}
        unmountOnExit
      >
        <Form form={form} layout="vertical">
          <FormItem label="名称" field="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如 检查 nginx 存活" />
          </FormItem>
          <FormItem label="对象类型" field="target_type" rules={[{ required: true, message: '请选择对象类型' }]}>
            <Select placeholder="选择对象类型">
              <Select.Option value="physical">物理机</Select.Option>
              <Select.Option value="service">系统服务</Select.Option>
              <Select.Option value="cluster">集群</Select.Option>
              <Select.Option value="pod">Pod</Select.Option>
            </Select>
          </FormItem>
          <FormItem label="操作系统发行版（留空 = 全部）" field="os_flavor">
            <Select allowClear placeholder="全部">
              <Select.Option value="ubuntu">Ubuntu</Select.Option>
              <Select.Option value="centos">CentOS</Select.Option>
            </Select>
          </FormItem>
          <FormItem label="描述" field="description">
            <Input.TextArea placeholder="可选描述" />
          </FormItem>
          <FormItem label="配置（JSON 阈值等）" field="config">
            <Input.TextArea placeholder='如 {"threshold": 90}' />
          </FormItem>
        </Form>
      </Modal>
    </div>
  );
}
