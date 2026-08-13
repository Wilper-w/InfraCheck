import type { ResultStatus } from '../types';
import { STATUS_META } from '../constants';

/** 结果状态标签：语义色 + 圆点，令牌驱动以支持深浅色。 */
export default function StatusTag({ status }: { status: ResultStatus }) {
  const meta = STATUS_META[status] ?? { text: status };
  return <span className={`status-tag status-${status}`}>{meta.text}</span>;
}

/** 巡检批次状态：非结果语义，用中性徽标，不占用四态色。 */
export function RunStatusTag({ status }: { status: string }) {
  const text = status === 'running' ? '运行中' : status === 'finished' ? '已完成' : '失败';
  if (status === 'failed') return <span className="status-tag status-abnormal">{text}</span>;
  if (status === 'running') return <span className="status-tag status-unreachable">{text}</span>;
  return <span className="status-tag status-normal">{text}</span>;
}
