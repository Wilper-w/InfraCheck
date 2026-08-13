import { useState } from 'react';
import { Tabs } from '@arco-design/web-react';
import PageHeader from '../components/PageHeader';
import EnvironmentsTab from '../components/config/EnvironmentsTab';
import NodesTab from '../components/config/NodesTab';
import ServicesTab from '../components/config/ServicesTab';
import CheckItemsTab from '../components/config/CheckItemsTab';

export default function Configuration() {
  const [activeKey, setActiveKey] = useState('environments');
  return (
    <div>
      <PageHeader title="环境配置" sub="维护环境、物理机、系统服务与巡检项的清单与配置" />
      <div className="panel-card" style={{ padding: '20px 20px 16px' }}>
        <Tabs activeTab={activeKey} onChange={setActiveKey} type="rounded">
          <Tabs.TabPane key="environments" title="环境" />
          <Tabs.TabPane key="nodes" title="物理机" />
          <Tabs.TabPane key="services" title="系统服务" />
          <Tabs.TabPane key="check-items" title="巡检项" />
          <Tabs.TabPane key="auto-inspection" title="自动巡检" />
        </Tabs>
        <div style={{ padding: '20px 4px 0' }}>
          {activeKey === 'environments' && <EnvironmentsTab />}
          {activeKey === 'nodes' && <NodesTab />}
          {activeKey === 'services' && <ServicesTab />}
          {activeKey === 'check-items' && <CheckItemsTab />}
        </div>
      </div>
    </div>
  );
}
