import { useEffect, useState } from 'react';
import { envApi } from '../api';
import type { Environment } from '../types';

/**
 * 环境下拉选择：加载环境清单并默认选中第一个。
 * 供物理机 / 系统服务等按环境归属的资源页使用。
 */
export function useEnvironments() {
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [envId, setEnvId] = useState<number | undefined>();

  useEffect(() => {
    void (async () => {
      try {
        const resp = await envApi.list({ page: 1, page_size: 100 });
        setEnvs(resp.items);
        setEnvId((cur) => cur ?? resp.items[0]?.id);
      } catch {
        /* 拦截器已提示 */
      }
    })();
  }, []);

  return {
    envs,
    envId,
    setEnvId,
    currentEnv: envs.find((e) => e.id === envId),
  };
}
