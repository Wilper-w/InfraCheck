import { useCallback, useEffect, useRef, useState } from 'react';
import { Form, Message } from '@arco-design/web-react';
import type { PageResult } from '../types';

/** 一张 CRUD 表格所需的接口。嵌套资源（如 /environments/{id}/nodes）
 *  由调用方闭包绑好父 id 后再传入，这里只面对统一形态。 */
export interface CrudApi<T, TInput> {
  list: (params: { page: number; page_size: number }) => Promise<PageResult<T>>;
  create: (data: TInput) => Promise<unknown>;
  update?: (id: number, data: Partial<TInput>) => Promise<unknown>;
  remove?: (id: number) => Promise<unknown>;
}

export interface CrudTableOptions<T, TInput> {
  api: CrudApi<T, TInput>;
  /** 操作成功后的提示语，各 Tab 用词不同（"已创建" / "已添加"），故完整给出 */
  labels: { created: string; updated?: string; deleted: string };
  pageSize?: number;
  /** 依赖未就绪时不加载（如尚未选定环境） */
  ready?: boolean;
  /** 变化时回到第 1 页重新加载（如切换环境） */
  resetKey?: unknown;
  /** 点击编辑时把记录映射为表单值；不传则该表格不支持编辑 */
  toFormValues?: (record: T) => Partial<TInput>;
  /** 新建时的表单预填值 */
  createDefaults?: Partial<TInput>;
}

/**
 * 列表 + 分页 + 新建/编辑弹窗 + 删除的通用逻辑。
 * 各 Tab 只需再写自己的 columns 与表单字段。
 */
export function useCrudTable<T extends { id: number }, TInput>({
  api,
  labels,
  pageSize = 10,
  ready = true,
  resetKey,
  toFormValues,
  createDefaults,
}: CrudTableOptions<T, TInput>) {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(ready);
  const [visible, setVisible] = useState(false);
  const [editing, setEditing] = useState<T | null>(null);
  const [form] = Form.useForm<TInput>();

  // api 由调用方在渲染中即时构造，引用每次都变；用 ref 隔离，避免进入依赖数组
  const apiRef = useRef(api);
  apiRef.current = api;

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      try {
        const resp = await apiRef.current.list({ page: p, page_size: pageSize });
        setItems(resp.items);
        setTotal(resp.total);
      } catch {
        /* 拦截器已提示 */
      } finally {
        setLoading(false);
      }
    },
    [pageSize],
  );

  // 首次挂载与 resetKey 变化时回到第 1 页；翻页走 changePage，二者不会重复触发
  useEffect(() => {
    setPage(1);
    if (ready) void load(1);
  }, [resetKey, ready, load]);

  const changePage = (p: number) => {
    setPage(p);
    void load(p);
  };

  const reload = () => load(page);

  // Arco 期望 DeepPartial<TInput>，泛型未解析时无法由 Partial<TInput> 推导，故在此收敛一次
  const setValues = (values: Partial<TInput>) =>
    form.setFieldsValue(values as Parameters<typeof form.setFieldsValue>[0]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    if (createDefaults) setValues(createDefaults);
    setVisible(true);
  };

  const openEdit = (record: T) => {
    if (!toFormValues) return;
    setEditing(record);
    setValues(toFormValues(record));
    setVisible(true);
  };

  const submit = async () => {
    const values = await form.validate();
    try {
      if (editing && apiRef.current.update) {
        await apiRef.current.update(editing.id, values);
        Message.success(labels.updated ?? labels.created);
      } else {
        await apiRef.current.create(values);
        Message.success(labels.created);
      }
      setVisible(false);
      await load(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  const remove = async (id: number) => {
    if (!apiRef.current.remove) return;
    try {
      await apiRef.current.remove(id);
      Message.success(labels.deleted);
      await load(page);
    } catch {
      /* 拦截器已提示 */
    }
  };

  return {
    items,
    total,
    page,
    loading,
    visible,
    setVisible,
    editing,
    form,
    openCreate,
    openEdit,
    submit,
    remove,
    reload,
    /** 直接展开给 Arco Table 的 pagination */
    pagination: {
      current: page,
      pageSize,
      total,
      showTotal: true,
      onChange: changePage,
    },
  };
}
