import { Component, type ReactNode } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Message, Result, Button } from '@arco-design/web-react';
import MainLayout from './layout/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Results from './pages/Results';
import Reports from './pages/Reports';
import Configuration from './pages/Configuration';
import AutoInspection from './pages/AutoInspection';
import Audit from './pages/Audit';

// 受保护路由包装：无 token 跳登录
function Protected({ children }: { children: ReactNode }) {
  const token = localStorage.getItem('infracheck_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// 错误边界：任一页面崩溃时给出可恢复提示，而非白屏
class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <Result
          status="error"
          title="页面渲染出错"
          subTitle={String(this.state.error.message || this.state.error)}
          extra={
            <Button type="primary" onClick={() => this.setState({ error: null })}>
              返回重试
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}

export default function App() {
  Message.config({ maxCount: 3, duration: 3000 });
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <Protected>
              <MainLayout />
            </Protected>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="results" element={<Results />} />
          <Route path="reports" element={<Reports />} />
          <Route path="configuration" element={<Configuration />} />
          <Route path="audit" element={<Audit />} />
          <Route path="auto-inspection" element={<AutoInspection />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ErrorBoundary>
  );
}
