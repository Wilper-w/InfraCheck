import type { ResultStatus } from './types';

// 结果状态 → 中文文案 + CSS 语义色令牌（深浅色自动适配）
export const STATUS_META: Record<
  ResultStatus,
  { text: string; cssVar: string }
> = {
  normal: { text: '正常', cssVar: 'var(--c-normal)' },
  abnormal: { text: '异常', cssVar: 'var(--c-abnormal)' },
  unreachable: { text: '不可达', cssVar: 'var(--c-unreachable)' },
  failed: { text: '检查失败', cssVar: 'var(--c-failed)' },
};

/** 图表序列：颜色走令牌，线型/形状提供非色彩区分（可及性） */
export const SERIES_META = [
  { key: 'normal' as const, label: '正常', cssVar: 'var(--c-normal)', dash: undefined, shape: 'circle' },
  { key: 'abnormal' as const, label: '异常', cssVar: 'var(--c-abnormal)', dash: '6 4', shape: 'square' },
  { key: 'unreachable' as const, label: '不可达', cssVar: 'var(--c-unreachable)', dash: '2 3', shape: 'triangle' },
  { key: 'failed' as const, label: '检查失败', cssVar: 'var(--c-failed)', dash: '4 3', shape: 'diamond' },
];

/** 系统服务探测方式（CONTRACT §3 system_services.probe_mode） */
export const PROBE_MODE_TEXT: Record<string, string> = {
  systemd: 'systemd',
  port: '端口监听',
  vip: 'VIP 绑定',
};

export const TARGET_TYPE_TEXT: Record<string, string> = {
  physical: '物理机',
  service: '系统服务',
  cluster: '集群',
  pod: 'Pod',
};

export const OS_FLAVOR_TEXT: Record<string, string> = {
  ubuntu: 'Ubuntu',
  centos: 'CentOS',
};

// 证据 verdict → 中文判读（用于结果表格展示）
export const VERDICT_TEXT: Record<string, string> = {
  pass: '通过',
  threshold_exceeded: '阈值超限',
  command_nonzero: '命令非零退出',
  check_command_error: '检查命令出错',
  host_unreachable: '目标不可达',
  connection_failed: '连接失败',
  connection_timeout: '连接超时',
  no_jump_host_configured: '未配置跳板机',
  no_target_address: '无目标地址',
};
