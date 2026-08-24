import api from './client';
import type {
  PageResult,
  LoginRequest,
  LoginResponse,
  MeResponse,
  Environment,
  EnvironmentInput,
  EnvironmentSummary,
  PhysicalNode,
  NodeInput,
  SystemService,
  ServiceInput,
  CheckItem,
  CheckItemInput,
  TargetType,
  Run,
  RunDetail,
  CheckResult,
  ResultStatus,
  DashboardSummary,
  TrendResponse,
  Report,
  AuditLog,
  AutoInspectionSetting,
  TopIssue,
  FindingInput,
  ScheduleEntry,
} from '../types';

// ---- auth ----
export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/auth/login', data).then((r) => r.data),
  me: () => api.get<MeResponse>('/auth/me').then((r) => r.data),
};

// ---- environments ----
export const envApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<PageResult<Environment>>('/environments', { params }).then((r) => r.data),
  create: (data: EnvironmentInput) =>
    api.post<Environment>('/environments', data).then((r) => r.data),
  update: (id: number, data: Partial<EnvironmentInput>) =>
    api.put<Environment>(`/environments/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/environments/${id}`).then((r) => r.data),
  summary: (id: number) =>
    api.get<EnvironmentSummary>(`/environments/${id}/summary`).then((r) => r.data),
};

// ---- physical nodes ----
export const nodeApi = {
  list: (
    envId: number,
    params?: { page?: number; page_size?: number },
  ) =>
    api
      .get<PageResult<PhysicalNode>>(`/environments/${envId}/nodes`, { params })
      .then((r) => r.data),
  create: (envId: number, data: NodeInput) =>
    api.post<PhysicalNode>(`/environments/${envId}/nodes`, data).then((r) => r.data),
  remove: (envId: number, nodeId: number) =>
    api.delete(`/environments/${envId}/nodes/${nodeId}`).then((r) => r.data),
};

// ---- system services ----
export const serviceApi = {
  list: (
    envId: number,
    params?: { page?: number; page_size?: number },
  ) =>
    api
      .get<PageResult<SystemService>>(`/environments/${envId}/services`, { params })
      .then((r) => r.data),
  create: (envId: number, data: ServiceInput) =>
    api.post<SystemService>(`/environments/${envId}/services`, data).then((r) => r.data),
  update: (envId: number, serviceId: number, data: Partial<ServiceInput>) =>
    api.put<SystemService>(`/environments/${envId}/services/${serviceId}`, data).then((r) => r.data),
  toggle: (envId: number, serviceId: number) =>
    api.post<SystemService>(`/environments/${envId}/services/${serviceId}/toggle`).then((r) => r.data),
  remove: (envId: number, serviceId: number) =>
    api.delete(`/environments/${envId}/services/${serviceId}`).then((r) => r.data),
};

// ---- check items ----
export const checkItemApi = {
  list: (params?: { enabled?: boolean; target_type?: TargetType; page?: number; page_size?: number }) =>
    api.get<PageResult<CheckItem>>('/check-items', { params }).then((r) => r.data),
  create: (data: CheckItemInput) =>
    api.post<CheckItem>('/check-items', data).then((r) => r.data),
  update: (id: number, data: Partial<CheckItemInput>) =>
    api.put<CheckItem>(`/check-items/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/check-items/${id}`).then((r) => r.data),
  toggle: (id: number) =>
    api.post<CheckItem>(`/check-items/${id}/toggle`).then((r) => r.data),
};

// ---- runs & results ----
export const runApi = {
  trigger: (data: {
    scope: 'all' | 'environment' | 'check';
    environment_id?: number;
    check_item_id?: number;
  }) => api.post<{ run_id: number }>('/runs/trigger', data).then((r) => r.data),
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<PageResult<Run>>('/runs', { params }).then((r) => r.data),
  detail: (id: number) => api.get<RunDetail>(`/runs/${id}`).then((r) => r.data),
  results: (
    id: number,
    params?: { status?: ResultStatus; object_type?: string; page?: number; page_size?: number },
  ) =>
    api
      .get<PageResult<CheckResult>>(`/runs/${id}/results`, { params })
      .then((r) => r.data),
};

// ---- dashboard ----
export const dashboardApi = {
  summary: () => api.get<DashboardSummary>('/dashboard/summary').then((r) => r.data),
  trend: (limit = 30) =>
    api.get<TrendResponse>('/dashboard/trend', { params: { limit } }).then((r) => r.data),
  topIssues: (limit = 5) =>
    api.get<TopIssue[]>('/dashboard/top-issues', { params: { limit } }).then((r) => r.data),
};

// ---- reports ----
export const reportApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<PageResult<Report>>('/reports', { params }).then((r) => r.data),
  htmlUrl: (id: number) => `/api/reports/${id}/html`,
  markdownUrl: (id: number) => `/api/reports/${id}/markdown`,
  // 通用导出：fetch 带 Bearer 拿 blob 落盘（HTML 或 Markdown）
  download: async (id: number, kind: 'html' | 'markdown', filename: string) => {
    const token = localStorage.getItem('infracheck_token');
    const resp = await fetch(`/api/reports/${id}/${kind}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw new Error(`导出失败: ${resp.status}`);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
  // 取原始 HTML（iframe 无法自带 Bearer，须 fetch 后注入）
  fetchHtml: async (id: number) => {
    const token = localStorage.getItem('infracheck_token');
    const resp = await fetch(`/api/reports/${id}/html`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw new Error(`加载失败: ${resp.status}`);
    return resp.text();
  },
};

// ---- audit ----
export const auditApi = {
  list: (params?: { actor?: string; page?: number; page_size?: number }) =>
    api.get<PageResult<AuditLog>>('/audit', { params }).then((r) => r.data),
};

// ---- settings: auto inspection schedule (time points) ----
export const settingsApi = {
  autoInspection: () =>
    api.get<AutoInspectionSetting>('/settings/auto-inspection').then((r) => r.data),
  updateAutoInspection: (data: { enabled?: boolean; schedules?: ScheduleEntry[] }) =>
    api.put<AutoInspectionSetting>('/settings/auto-inspection', data).then((r) => r.data),
};

// ---- findings (anomaly triage) ----
export const findingsApi = {
  set: (data: FindingInput) => api.post('/findings', data).then((r) => r.data),
};
