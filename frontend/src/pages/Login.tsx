import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, Button, Message } from '@arco-design/web-react';
import { IconUser } from '@arco-design/web-react/icon';
import { authApi } from '../api';

export default function Login() {
  const navigate = useNavigate();
  const [account, setAccount] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!account.trim()) {
      Message.warning('请输入巡检人账号');
      return;
    }
    setLoading(true);
    try {
      const { token, account: acct } = await authApi.login({ account: account.trim() });
      localStorage.setItem('infracheck_token', token);
      localStorage.setItem('infracheck_account', acct);
      Message.success(`欢迎，${acct}`);
      navigate('/', { replace: true });
    } catch {
      /* 错误已由拦截器提示 */
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 16px',
        background: 'var(--c-bg)',
      }}
    >
      <div style={{ width: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--s-8)' }}>
          <div
            style={{
              width: 48,
              height: 48,
              margin: '0 auto var(--s-4)',
              borderRadius: 'var(--r-xl)',
              background: 'var(--c-primary)',
              color: '#fff',
              fontSize: 18,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              letterSpacing: '-0.5px',
            }}
          >
            IC
          </div>
          <div style={{ color: 'var(--c-text)', fontSize: 22, fontWeight: 650, letterSpacing: '-0.01em' }}>
            InfraCheck 巡检平台
          </div>
          <div style={{ color: 'var(--c-text-muted)', marginTop: 6, fontSize: 'var(--fs-md)' }}>
            多环境自动化巡检 · 健康看板 · 双格式报告
          </div>
        </div>

        <div
          style={{
            background: 'var(--c-surface)',
            borderRadius: 'var(--r-xl)',
            padding: 'var(--s-8) var(--s-8) var(--s-6)',
            border: '1px solid var(--c-border)',
            boxShadow: 'var(--sh-md)',
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 'var(--fs-lg)', marginBottom: 4 }}>账号登录</div>
          <div className="sub-text" style={{ marginBottom: 'var(--s-6)' }}>
            使用企业微信（云效）账号，未授权请联系平台管理员开通
          </div>

          <label htmlFor="login-account" style={{ display: 'block', fontWeight: 500, fontSize: 'var(--fs-md)', marginBottom: 6 }}>
            账号
          </label>
          <Input
            id="login-account"
            prefix={<IconUser />}
            placeholder="输入巡检人账号，如 zhangsan"
            value={account}
            onChange={setAccount}
            onPressEnter={handleSubmit}
            size="large"
            autoComplete="username"
          />
          <Button
            type="primary"
            long
            size="large"
            loading={loading}
            onClick={handleSubmit}
            style={{ marginTop: 'var(--s-5)' }}
          >
            登录
          </Button>
        </div>

        <div style={{ textAlign: 'center', marginTop: 'var(--s-5)' }} className="sub-text">
          InfraCheck · 自动化巡检与报告平台
        </div>
      </div>
    </div>
  );
}
