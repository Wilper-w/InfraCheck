import { Tag } from '@arco-design/web-react';
import type { ResultStatus } from '../types';
import { STATUS_META } from '../constants';

/** 结果状态统一标签（颜色 + 文案，居中固定宽度） */
export default function StatusTag({ status }: { status: ResultStatus }) {
  const meta = STATUS_META[status] ?? { color: 'gray', text: status };
  return (
    <Tag className="status-tag" color={meta.color}>
      {meta.text}
    </Tag>
  );
}

export const RUN_STATUS_META: Record<string, { color: string; text: string }> = {
  running: { color: 'arcoblue', text: '运行中' },
  finished: { color: 'green', text: '已完成' },
  failed: { color: 'red', text: '失败' },
};
