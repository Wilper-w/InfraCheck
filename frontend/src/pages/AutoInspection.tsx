import { useEffect, useState, useCallback } from 'react';
import {
  Switch,
  Button,
  Message,
  Spin,
  Alert,
  TimePicker,
  Checkbox,
  Space,
} from '@arco-design/web-react';
import { IconSave, IconPlus, IconDelete } from '@arco-design/web-react/icon';
import { settingsApi } from '../api';
import PageHeader from '../components/PageHeader';
import type { AutoInspectionSetting, ScheduleEntry, WeekDay } from '../types';

const fmtTime = (s: string | null) =>
  s
    ? new Date(s).toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    : '—';

const DAYS_TEXT: Record<number, string> = {
  0: '周一',
  1: '周二',
  2: '周三',
  3: '周四',
  4: '周五',
  5: '周六',
  6: '周日',
};
const DAY_OPTIONS = [0, 1, 2, 3, 4, 5, 6].map((d) => ({ label: DAYS_TEXT[d], value: d }));

const dayLabel = (days: number[]) =>
  days.length === 0 ? '每天' : days.map((d) => DAYS_TEXT[d]).join('、');

export default function AutoInspection() {
  const [enabled, setEnabled] = useState(false);
  const [schedules, setSchedules] = useState<ScheduleEntry[]>([]);
  const [nextRuns, setNextRuns] = useState<
    Array<{ time: string; days: WeekDay[]; next_run_at: string | null }>
  >([]);
  const [lastRun, setLastRun] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const s: AutoInspectionSetting = await settingsApi.autoInspection();
      setEnabled(s.enabled);
      setSchedules(s.schedules && s.schedules.length ? s.schedules : [{ time: '09:00', days: [] }]);
      setNextRuns(s.next_run_times || []);
      setLastRun(s.last_scheduled_run_at);
    } catch {
      /* 拦截器已提示 */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updateTime = (i: number, time: string) =>
    setSchedules((prev) => prev.map((s, idx) => (idx === i ? { ...s, time } : s)));
  const updateDays = (i: number, days: number[]) =>
    setSchedules((prev) =>
      prev.map((s, idx) => (idx === i ? { ...s, days: days as WeekDay[] } : s)),
    );
  const removeAt = (i: number) => setSchedules((prev) => prev.filter((_, idx) => idx !== i));
  const addAt = () => setSchedules((prev) => [...prev, { time: '09:00', days: [] }]);

  const handleSave = async () => {
    if (schedules.length === 0) {
      Message.warning('请至少保留一个巡检时间点');
      return;
    }
    setSaving(true);
    try {
      const s: AutoInspectionSetting = await settingsApi.updateAutoInspection({ enabled, schedules });
      setSchedules(s.schedules);
      setNextRuns(s.next_run_times || []);
      setLastRun(s.last_scheduled_run_at);
      Message.success('定时任务已保存并生效');
    } catch {
      /* 拦截器已提示 */
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size={32} tip="加载调度设置..." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="定时任务"
        sub="按设定的时间点周期性巡检全部环境，可配置多个时刻（如每天 08:00 与 22:00）"
        actions={
          <Button type="primary" icon={<IconSave />} loading={saving} onClick={handleSave}>
            保存并生效
          </Button>
        }
      />

      {!enabled && (
        <Alert
          type="warning"
          style={{ marginBottom: 'var(--s-4)' }}
          content="当前定时任务已关闭，平台仅在手动点击「立即巡检」时执行。"
        />
      )}

      <div className="panel-card" style={{ width: '100%' }}>
        <div className="card-head">
          <div>
            <div className="card-title">启用定时任务</div>
            <div className="sub-text" style={{ marginTop: 2 }}>
              开启后按下方时间点自动巡检全部环境
            </div>
          </div>
          <Switch checked={enabled} onChange={setEnabled} checkedText="开" uncheckedText="关" />
        </div>

        <div className="card-body">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 'var(--s-3)',
            }}
          >
            <span style={{ fontWeight: 600 }}>巡检时间点</span>
            <Button size="small" icon={<IconPlus />} onClick={addAt}>
              添加时间点
            </Button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            {schedules.map((s, i) => (
              <div
                key={i}
                style={{
                  background: 'var(--c-fill)',
                  border: '1px solid var(--c-border)',
                  borderRadius: 'var(--r-md)',
                  padding: 'var(--s-4)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: 'var(--s-3)',
                  }}
                >
                  <Space size={12}>
                    <span className="sub-text">时刻</span>
                    <TimePicker
                      format="HH:mm"
                      value={s.time}
                      onChange={(v) => updateTime(i, v || '09:00')}
                      style={{ width: 128 }}
                    />
                  </Space>
                  <Button
                    type="text"
                    status="danger"
                    size="small"
                    icon={<IconDelete />}
                    disabled={schedules.length === 1}
                    onClick={() => removeAt(i)}
                  >
                    删除
                  </Button>
                </div>
                <div className="sub-text" style={{ marginBottom: 6 }}>
                  执行星期（不勾选即每天执行）
                </div>
                <Checkbox.Group
                  options={DAY_OPTIONS}
                  value={s.days}
                  onChange={(v) => updateDays(i, (Array.isArray(v) ? v : []).map(Number))}
                  direction="horizontal"
                />
              </div>
            ))}
          </div>

          <div
            style={{
              marginTop: 'var(--s-5)',
              paddingTop: 'var(--s-4)',
              borderTop: '1px solid var(--c-border)',
              display: 'grid',
              gridTemplateColumns: 'auto 1fr',
              gap: '8px 16px',
              fontSize: 'var(--fs-sm)',
            }}
          >
            <span style={{ color: 'var(--c-text-muted)' }}>最近一次定时巡检</span>
            <span className="num">{fmtTime(lastRun)}</span>
            <span style={{ color: 'var(--c-text-muted)' }}>下次执行计划</span>
            <span>
              {nextRuns.length
                ? nextRuns
                    .map(
                      (r) =>
                        `每日 ${r.time}（${dayLabel(r.days)}）${
                          r.next_run_at ? ' → ' + fmtTime(r.next_run_at) : ''
                        }`,
                    )
                    .join('；')
                : '—'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
