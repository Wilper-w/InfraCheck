import { Spin, Empty, Result } from '@arco-design/web-react';
import type { ReactNode } from 'react';

/** 统一加载态 */
export function LoadingState({ tip = '加载中...' }: { tip?: string }) {
  return (
    <div style={{ textAlign: 'center', padding: 60 }}>
      <Spin size={32} tip={tip} />
    </div>
  );
}

/** 统一空态 */
export function EmptyState({ description = '暂无数据' }: { description?: string }) {
  return <Empty description={description} style={{ padding: 40 }} />;
}

/** 统一错误态 */
export function ErrorState({ message = '加载失败', onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <Result
      status="error"
      title="数据加载失败"
      subTitle={message}
      extra={onRetry ? <button onClick={onRetry} style={{ color: 'var(--color-primary)', cursor: 'pointer', background: 'none', border: 'none', fontWeight: 600 }}>重新加载</button> : undefined}
    />
  );
}

/** 条件渲染三态：loading / error / empty / data */
export function AsyncState<T>({
  loading, error, data, onRetry, emptyText, children,
}: {
  loading: boolean;
  error: string | null;
  data: T[] | null | undefined;
  onRetry?: () => void;
  emptyText?: string;
  children: () => ReactNode;
}) {
  if (loading && !data) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (data && data.length === 0) return <EmptyState description={emptyText || '暂无数据'} />;
  return <>{children()}</>;
}
