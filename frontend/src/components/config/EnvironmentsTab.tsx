import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Popconfirm,
  Tag,
  Typography,
  Empty,
} from '@arco-design/web-react';
import type { TableColumnProps } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { envApi } from '../../api';
import { useCrudTable } from '../../hooks/useCrudTable';
import type { Environment, EnvironmentInput } from '../../types';

const { Text } = Typography;
const FormItem = Form.Item;

export default function EnvironmentsTab() {
  const crud = useCrudTable<Environment, EnvironmentInput>({
    api: envApi,
    labels: { created: '环境已创建', updated: '环境已更新', deleted: '环境已删除' },
    toFormValues: (r) => ({
      name: r.name,
      os_flavor: r.os_flavor,
      description: r.description,
    }),
  });

  const columns: TableColumnProps<Environment>[] = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    {
      title: '名称',
      dataIndex: 'name',
      render: (v: string) => <Text bold>{v}</Text>,
    },
    {
      title: '操作系统',
      dataIndex: 'os_flavor',
      width: 140,
      resizable: true,
      render: (v: string) =>
        v === 'ubuntu' ? (
          <Tag color="arcoblue">Ubuntu 22/24</Tag>
        ) : v === 'centos' ? (
          <Tag color="orangered">CentOS 8</Tag>
        ) : (
          v
        ),
    },
    { title: '描述', dataIndex: 'description', render: (v: string) => v || '-' },
    { title: '创建时间', dataIndex: 'created_at', width: 180, render: (v: string) => new Date(v).toLocaleString('zh-CN', { hour12: false }) },
    {
      title: '操作',
      key: 'action',
      width: 150,
      resizable: true,
      render: (_: unknown, record: Environment) => (
        <Space>
          <Button type="text" size="small" onClick={() => crud.openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该环境？该环境下的节点、服务将一并删除。" onOk={() => crud.remove(record.id)}>
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
          <div style={{ fontWeight: 600, fontSize: 15 }}>环境管理</div>
          <div className="sub-text" style={{ marginTop: 4 }}>维护 5 套网络隔离环境的清单与操作系统发行版</div>
        </div>
        <Button type="primary" icon={<IconPlus />} onClick={crud.openCreate}>
          新建环境
        </Button>
      </div>

      <Table
        rowKey="id"
        loading={crud.loading}
        columns={columns}
        data={crud.items}
        borderCell
        pagination={crud.pagination}
        noDataElement={<Empty description="暂无环境" />}
      />

      <Modal
        title={crud.editing ? '编辑环境' : '新建环境'}
        visible={crud.visible}
        onCancel={() => crud.setVisible(false)}
        onOk={crud.submit}
        unmountOnExit
      >
        <Form form={crud.form} layout="vertical" requiredSymbol={true}>
          <FormItem label="名称" field="name" rules={[{ required: true, message: '请输入环境名称' }]}>
            <Input placeholder="如 env-01" />
          </FormItem>
          <FormItem label="操作系统发行版" field="os_flavor" rules={[{ required: true, message: '请选择操作系统' }]}>
            <Select placeholder="选择发行版">
              <Select.Option value="ubuntu">Ubuntu</Select.Option>
              <Select.Option value="centos">CentOS</Select.Option>
            </Select>
          </FormItem>
          <FormItem label="描述" field="description">
            <Input.TextArea placeholder="可选描述" />
          </FormItem>
        </Form>
      </Modal>
    </div>
  );
}
