import axios, { AxiosError } from 'axios';
import { Message } from '@arco-design/web-react';

// 全局 axios 实例：自动携带 Bearer token，401 时清除 token并跳登录。
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('infracheck_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('infracheck_token');
      localStorage.removeItem('infracheck_account');
      // 避免在登录页死循环
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    const detail = error.response?.data?.detail || error.message || '请求失败';
    // 401 跳转时不弹消息
    if (error.response?.status !== 401) {
      Message.error(detail);
    }
    return Promise.reject(error);
  },
);

export default api;
