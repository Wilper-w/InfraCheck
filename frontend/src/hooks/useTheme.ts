import { useCallback, useEffect, useState } from 'react';

const KEY = 'infracheck_theme';
export type Theme = 'light' | 'dark';

/** 与 Arco 同源的主题切换：body[arco-theme] 同时驱动 Arco 组件与自定义令牌。 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(KEY) as Theme) || 'light',
  );

  useEffect(() => {
    if (theme === 'dark') document.body.setAttribute('arco-theme', 'dark');
    else document.body.removeAttribute('arco-theme');
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const toggle = useCallback(
    () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')),
    [],
  );

  return { theme, toggle };
}
