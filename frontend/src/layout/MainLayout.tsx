import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, Message, Tooltip } from '@arco-design/web-react';
import {
  IconDashboard,
  IconList,
  IconFile,
  IconSettings,
  IconHistory,
  IconUser,
  IconPoweroff,
  IconClockCircle,
  IconMoonFill,
  IconSunFill,
} from '@arco-design/web-react/icon';
import { settingsApi } from '../api';
import { useTheme } from '../hooks/useTheme';
import type { AutoInspectionSetting } from '../types';

const { Sider, Header, Content } = Layout;

/** 按职能分组，避免菜单项增长后变成一条无结构的长列表 */
const navGroups = [
  {
    title: '监控',
    items: [
      { key: '/', label: '总览', icon: <IconDashboard /> },
      { key: '/results', label: '巡检结果', icon: <IconList /> },
      { key: '/reports', label: '报告归档', icon: <IconFile /> },
    ],
  },
  {
    title: '配置',
    items: [
      { key: '/configuration', label: '环境配置', icon: <IconSettings /> },
      { key: '/auto-inspection', label: '定时任务', icon: <IconClockCircle /> },
    ],
  },
  {
    title: '系统',
    items: [{ key: '/audit', label: '审计日志', icon: <IconHistory /> }],
  },
];

const allItems = navGroups.flatMap((g) => g.items);

const fmtNext = (iso: string) =>
  new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const account = localStorage.getItem('infracheck_account') || '巡检人';
  const { theme, toggle } = useTheme();
  const [autoStatus, setAutoStatus] = useState<AutoInspectionSetting | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setAutoStatus(await settingsApi.autoInspection());
      } catch {
        /* ignore */
      }
    };
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const selectedKey =
    allItems.find((m) => m.key !== '/' && location.pathname.startsWith(m.key))?.key || '/';

  const handleLogout = () => {
    localStorage.removeItem('infracheck_token');
    localStorage.removeItem('infracheck_account');
    Message.success('已退出登录');
    navigate('/login', { replace: true });
  };

  const nextRun = autoStatus?.next_run_times?.[0]?.next_run_at;

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider width={216} className="app-sider">
        <div className="app-logo">
          <span className="app-logo-mark">IC</span>
          <span>InfraCheck</span>
        </div>

        <div style={{ overflowY: 'auto', height: 'calc(100% - var(--header-h))' }}>
          {navGroups.map((group) => (
            <div key={group.title}>
              <div className="nav-group">{group.title}</div>
              <Menu
                selectedKeys={[selectedKey]}
                onClickMenuItem={(key) => navigate(key)}
                style={{ width: '100%' }}
              >
                {group.items.map((item) => (
                  <Menu.Item key={item.key}>
                    {item.icon}
                    {item.label}
                  </Menu.Item>
                ))}
              </Menu>
            </div>
          ))}
        </div>
      </Sider>

      <Layout>
        {/* 顶栏只承载全局状态与操作；页面标题由各页 PageHeader 唯一提供 */}
        <Header className="app-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-2)' }}>
            {autoStatus && (
              <span
                className={autoStatus.enabled ? 'status-tag status-normal' : 'status-tag status-failed'}
                title={nextRun ? `下次执行 ${fmtNext(nextRun)}` : undefined}
              >
                定时巡检{autoStatus.enabled ? '已开启' : '已关闭'}
                {autoStatus.enabled && nextRun && (
                  <span style={{ opacity: 0.75, fontWeight: 400 }}>· 下次 {fmtNext(nextRun)}</span>
                )}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-1)' }}>
            <Tooltip content={theme === 'dark' ? '切换到浅色' : '切换到深色'}>
              <button
                className="header-action"
                onClick={toggle}
                aria-label={theme === 'dark' ? '切换到浅色主题' : '切换到深色主题'}
              >
                {theme === 'dark' ? <IconSunFill /> : <IconMoonFill />}
              </button>
            </Tooltip>

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
              <span className="header-action">
                <Avatar size={24} style={{ backgroundColor: 'var(--c-primary)' }}>
                  <IconUser />
                </Avatar>
                <span style={{ fontWeight: 500, color: 'var(--c-text)' }}>{account}</span>
              </span>
            </Dropdown>
          </div>
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
