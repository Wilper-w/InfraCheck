import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Message,
  Tag,
} from '@arco-design/web-react';
import {
  IconDashboard,
  IconList,
  IconFile,
  IconSettings,
  IconHistory,
  IconUser,
  IconPoweroff,
  IconClockCircle,
} from '@arco-design/web-react/icon';
import { settingsApi } from '../api';
import type { AutoInspectionSetting } from '../types';

const { Sider, Header, Content } = Layout;

const menuItems = [
  { key: '/', label: '总览', icon: <IconDashboard /> },
  { key: '/results', label: '巡检结果', icon: <IconList /> },
  { key: '/reports', label: '报告归档', icon: <IconFile /> },
  { key: '/configuration', label: '环境配置', icon: <IconSettings /> },
  { key: '/auto-inspection', label: '定时任务', icon: <IconClockCircle /> },
  { key: '/audit', label: '审计日志', icon: <IconHistory /> },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const account = localStorage.getItem('infracheck_account') || '巡检人';
  const [collapsed, setCollapsed] = useState(false);
  const [autoStatus, setAutoStatus] = useState<AutoInspectionSetting | null>(null);

  useEffect(() => {
    const load = async () => { try { setAutoStatus(await settingsApi.autoInspection()); } catch { /* ignore */ } };
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const selectedKey =
    menuItems.find((m) => m.key !== '/' && location.pathname.startsWith(m.key))?.key ||
    '/';
  const currentLabel = menuItems.find((m) => m.key === selectedKey)?.label || '';

  const handleLogout = () => {
    localStorage.removeItem('infracheck_token');
    localStorage.removeItem('infracheck_account');
    Message.success('已退出登录');
    navigate('/login', { replace: true });
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={224}
        className="app-sider"
      >
        <div
          className="app-logo"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            color: 'var(--color-text)',
            fontWeight: 700,
            fontSize: collapsed ? 14 : 16,
            letterSpacing: 0.5,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          <span
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              background: 'linear-gradient(135deg,#165dff,#3c7dff)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 14,
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            IC
          </span>
          {!collapsed && (
            <span>
              InfraCheck
              <span
                style={{
                  marginLeft: 8,
                  fontSize: 12,
                  color: '#86909c',
                  fontWeight: 400,
                  letterSpacing: 1,
                }}
              >
                巡检平台
              </span>
            </span>
          )}
        </div>
        <Menu
          theme="light"
          selectedKeys={[selectedKey]}
          onClickMenuItem={(key) => navigate(key)}
          style={{ width: '100%', paddingTop: 8 }}
        >
          {menuItems.map((item) => (
            <Menu.Item key={item.key}>
              {item.icon}
              {item.label}
            </Menu.Item>
          ))}
        </Menu>
      </Sider>
      <Layout>
        <Header
          style={{
            height: 56,
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            borderBottom: '1px solid #e5e6eb',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Tag color="arcoblue" size="medium" style={{ fontWeight: 600 }}>
              {currentLabel}
            </Tag>
            {autoStatus && (
              <Tag color={autoStatus.enabled ? 'green' : 'gray'} size="medium" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <IconClockCircle />
                {autoStatus.enabled ? '自动巡检 开' : '自动巡检 关'}
                {autoStatus.next_run_times && autoStatus.next_run_times.length > 0 && (
                  <span style={{ fontSize: 11, opacity: 0.8 }}>· 下次 {new Date(autoStatus.next_run_times[0].next_run_at || '').toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })}</span>
                )}
              </Tag>
            )}
          </div>
          <Dropdown
            droplist={
              <Menu onClickMenuItem={(key) => key === 'logout' && handleLogout()}>
                <Menu.Item key="logout">
                  <IconPoweroff style={{ marginRight: 8 }} />
                  退出登录
                </Menu.Item>
              </Menu>
            }
            position="br"
          >
            <span
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '4px 8px',
                borderRadius: 6,
              }}
            >
              <Avatar size={28} style={{ backgroundColor: '#165dff' }}>
                <IconUser />
              </Avatar>
              <span style={{ fontWeight: 500 }}>{account}</span>
            </span>
          </Dropdown>
        </Header>
        <Content className="app-content">
          <div className="page-wrap">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
