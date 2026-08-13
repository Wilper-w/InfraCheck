import type { ResultStatus } from './types';

// 结果状态 → Arco Tag 颜色 + 中文文案
export const STATUS_META: Record<
  ResultStatus,
  { color: string; text: string }
> = {
  normal: { color: 'green', text: '正常' },
  abnormal: { color: 'red', text: '异常' },
  unreachable: { color: 'orange', text: '不可达' },
  failed: { color: 'gray', text: '检查失败' },
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
