import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  sub?: string;
  actions?: ReactNode;
}

/** 统一页头：标题 + 副标题 + 右侧操作区 */
export default function PageHeader({ title, sub, actions }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div>
        <h2 className="page-title">{title}</h2>
        {sub && <p className="page-sub">{sub}</p>}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  );
}
