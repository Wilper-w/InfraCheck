// 与 CONTRACT.md §3 数据模型 & §4 REST API 对应的类型定义

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// auth
export interface LoginRequest {
  account: string;
}
export interface LoginResponse {
  token: string;
  account: string;
}
export interface MeResponse {
  account: string;
}

// environments
export type OsFlavor = 'ubuntu' | 'centos';
export interface Environment {
  id: number;
  name: string;
  os_flavor: OsFlavor;
  description: string;
  created_at: string;
}
export interface EnvironmentInput {
  name: string;
  os_flavor: OsFlavor;
  description?: string;
}
export interface EnvironmentSummary {
  environment_id: number;
  environment_name: string;
  os_flavor: OsFlavor;
  total: number;
  normal: number;
  abnormal: number;
  unreachable: number;
  failed: number;
}

// physical nodes
export interface PhysicalNode {
  id: number;
  environment_id: number;
  hostname: string;
  ip: string;
  os_flavor: string | null;
  created_at: string;
}
export interface NodeInput {
  hostname: string;
  ip: string;
  os_flavor?: string;
}

// system services
/** 探测方式：systemd 单元状态 | 端口监听 | VIP 绑定（keepalived 等） */
export type ProbeMode = 'systemd' | 'port' | 'vip';

export interface SystemService {
  id: number;
  environment_id: number;
  node_id: number | null;
  name: string;
  port: number | null;
  enabled: boolean;
  probe_mode: ProbeMode;
  probe_target: string | null;
}
export interface ServiceInput {
  name: string;
  node_id?: number | null;
  port?: number | null;
  enabled?: boolean;
  probe_mode?: ProbeMode;
  probe_target?: string | null;
}

// check items
export type TargetType = 'physical' | 'service' | 'cluster' | 'pod';
export interface CheckItem {
  id: number;
  name: string;
  target_type: TargetType;
  os_flavor: string | null;
  description: string;
  enabled: boolean;
  config: string;
}
export interface CheckItemInput {
  name: string;
  target_type: TargetType;
  os_flavor?: string | null;
  description?: string;
  config?: string;
}

// runs & results
export type RunStatus = 'running' | 'finished' | 'failed';
export interface Run {
  id: number;
  trigger: string;
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
  status: RunStatus;
}
export interface RunDetail extends Run {
  results?: {
    total: number;
    normal: number;
    abnormal: number;
    unreachable: number;
    failed: number;
  };
}
export type ResultStatus = 'normal' | 'abnormal' | 'unreachable' | 'failed';
export interface CheckResult {
  id: number;
  run_id: number;
  check_item_id: number;
  object_type: string;
  object_name: string;
  environment_id: number;
  os_flavor: string | null;
  status: ResultStatus;
  evidence: string;
  captured_at: string;
}

// dashboard
export interface DashboardSummary {
  generated_at: string;
  total: number;
  normal: number;
  abnormal: number;
  unreachable: number;
  failed: number;
  environments: {
    environment_id: number;
    name: string;
    os_flavor: string;
    normal: number;
    abnormal: number;
    unreachable: number;
    failed: number;
    total: number;
  }[];
}
export type FindingState = 'pending' | 'resolved' | 'ignored';
export interface TopIssue {
  check_item_id: number;
  object_type: string;
  object_name: string;
  environment_id: number;
  environment_name: string;
  status: ResultStatus;
  evidence: string;
  captured_at: string;
  state: FindingState;
  note?: string;
}
export interface FindingInput {
  check_item_id: number;
  object_type: string;
  object_name: string;
  environment_id: number;
  state: FindingState;
  note?: string;
}
export interface TrendPoint {
  date: string;
  normal: number;
  abnormal: number;
  unreachable: number;
  failed: number;
}
export interface TrendResponse {
  series: TrendPoint[];
}

// reports
export interface Report {
  id: number;
  run_id: number;
  rendered_by: string;
  generated_at: string;
  html_path: string;
  md_path: string;
}

// audit
export interface AuditLog {
  id?: number;
  actor: string;
  action: string;
  target_ref: string | null;
  detail: string;
  created_at: string;
}

// settings: auto inspection (time-point schedules)
export type WeekDay = 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0=周一 .. 6=周日
export interface ScheduleEntry {
  time: string; // "HH:MM"
  days: WeekDay[]; // 空 = 每天
}
export interface ScheduleNextRun {
  time: string;
  days: WeekDay[];
  next_run_at: string | null;
}
export interface AutoInspectionSetting {
  enabled: boolean;
  schedules: ScheduleEntry[];
  next_run_times: ScheduleNextRun[];
  last_scheduled_run_at: string | null;
}
