import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, Button, Message, Typography } from '@arco-design/web-react';
import { IconUser } from '@arco-design/web-react/icon';
import { authApi } from '../api';

const { Paragraph } = Typography;

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
        background:
          'linear-gradient(160deg, #eef4ff 0%, #f7faff 45%, #eaf2ff 100%)',
      }}
    >
      <div style={{ width: 420 }}>
        {/* 品牌区 */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div
            style={{
              width: 60,
              height: 60,
              margin: '0 auto 18px',
              borderRadius: 16,
              background: 'linear-gradient(135deg,#165dff,#3c7dff)',
              color: '#fff',
              fontSize: 26,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 10px 30px rgba(22,93,255,0.25)',
            }}
          >
            IC
          </div>
          <div style={{ color: '#1d2129', fontSize: 24, fontWeight: 700, letterSpacing: 1 }}>
            InfraCheck 巡检平台
          </div>
          <Paragraph
            style={{
              color: '#6b7280',
              marginTop: 10,
              marginBottom: 0,
              fontSize: 14,
            }}
          >
            多环境自动化巡检 · 健康看板 · 双格式报告
          </Paragraph>
        </div>

        {/* 登录卡片 */}
        <div
          style={{
            background: '#ffffff',
            borderRadius: 14,
            padding: '32px 30px 26px',
            border: '1px solid #e8edf5',
            boxShadow: '0 16px 48px rgba(31,56,88,0.08)',
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 17, marginBottom: 6 }}>账号登录</div>
          <div className="sub-text" style={{ marginBottom: 24 }}>
            使用企业微信（云效）账号，未授权请联系平台管理员开通
          </div>
          <div>
            <div style={{ fontWeight: 500, fontSize: 14, marginBottom: 8 }}>账号</div>
            <Input
              prefix={<IconUser />}
              placeholder="输入巡检人账号，如 zhangsan"
              value={account}
              onChange={setAccount}
              onPressEnter={handleSubmit}
              size="large"
              autoComplete="username"
            />
            <Button type="primary" long size="large" loading={loading} onClick={handleSubmit} style={{ marginTop: 20 }}>
              登录
            </Button>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: 18 }} className="sub-text">
          InfraCheck · 自动化巡检与报告平台
        </div>
      </div>
    </div>
  );
}
