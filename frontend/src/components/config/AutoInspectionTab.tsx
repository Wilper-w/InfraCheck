import { useEffect, useState, useCallback } from 'react';
import {
  Switch,
  Button,
  Message,
  Spin,
  Descriptions,
  Alert,
  TimePicker,
  Checkbox,
  Card,
  Space,
  Tag,
} from '@arco-design/web-react';
import {
  IconSave,
  IconCalendarClock,
  IconPlus,
  IconDelete,
} from '@arco-design/web-react/icon';
import { settingsApi } from '../../api';
import type { AutoInspectionSetting, ScheduleEntry, WeekDay } from '../../types';

const fmtTime = (s: string | null) =>
  s ? new Date(s).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }) : '—';

const DAYS_TEXT: Record<number, string> = { 0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日' };
const DAY_OPTIONS = [0, 1, 2, 3, 4, 5, 6].map((d) => ({ label: DAYS_TEXT[d], value: d }));

const dayLabel = (days: number[]) => (days.length === 0 ? '每天' : days.map((d) => DAYS_TEXT[d]).join('、'));

export default function AutoInspectionTab() {
  const [enabled, setEnabled] = useState(false);
  const [schedules, setSchedules] = useState<ScheduleEntry[]>([]);
  const [nextRuns, setNextRuns] = useState<Array<{ time: string; days: WeekDay[]; next_run_at: string | null }>>([]);
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

  const updateTime = (i: number, time: string) => {
    setSchedules((prev) => prev.map((s, idx) => (idx === i ? { ...s, time } : s)));
  };
  const updateDays = (i: number, days: number[]) => {
    setSchedules((prev) => prev.map((s, idx) => (idx === i ? { ...s, days: days as WeekDay[] } : s)));
  };
  const removeAt = (i: number) => setSchedules((prev) => prev.filter((_, idx) => idx !== i));
  const addAt = () => setSchedules((prev) => [...prev, { time: '09:00', days: [] }]);

  const handleSave = async () => {
    if (schedules.length === 0) {
      Message.warning('请至少保留一个巡检时间点');
      return;
    }
    setSaving(true);
    try {
      const s: AutoInspectionSetting = await settingsApi.updateAutoInspection({
        enabled,
        schedules,
      });
      setSchedules(s.schedules);
      setNextRuns(s.next_run_times || []);
      setLastRun(s.last_scheduled_run_at);
      Message.success('自动巡检时间点已保存并生效');
    } catch {
      /* 拦截器已提示 */
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size={32} tip="加载调度设置..." />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>自动巡检</div>
          <div className="sub-text" style={{ marginTop: 4 }}>
            按设定的时间点周期性巡检，可配置多个时刻（如每天 08:00 与 22:00）
          </div>
        </div>
        <IconCalendarClock style={{ fontSize: 26, color: 'var(--color-primary)' }} />
      </div>

      {!enabled && (
        <Alert
          type="warning"
          style={{ marginBottom: 20 }}
          content="当前自动巡检处于关闭状态，平台仅在手动点击「立即巡检」时执行。"
        />
      )}

      <div className="panel-card" style={{ padding: 24 }}>
        {/* 启用开关 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0 20px', borderBottom: '1px solid var(--color-border)' }}>
          <div>
            <div style={{ fontWeight: 600 }}>启用自动巡检</div>
            <div className="sub-text" style={{ marginTop: 4 }}>开启后按下方时间点自动巡检全部环境</div>
          </div>
          <Switch checked={enabled} onChange={setEnabled} checkedText="开" uncheckedText="关" />
        </div>

        {/* 时间点列表 */}
        <div style={{ marginTop: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontWeight: 600 }}>巡检时间点</span>
            <Button size="small" icon={<IconPlus />} onClick={addAt}>
              添加时间点
            </Button>
          </div>

          {schedules.length === 0 ? (
            <div className="sub-text" style={{ padding: '20px 0', textAlign: 'center' }}>
              暂无时间点，点击「添加时间点」配置（如 08:00、22:00）
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {schedules.map((s, i) => (
                <Card key={i} bordered={false} style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, justifyContent: 'space-between' }}>
                      <Space size={12}>
                        <span className="sub-text">时刻</span>
                        <TimePicker
                          format="HH:mm"
                          value={s.time}
                          onChange={(v) => updateTime(i, v || '09:00')}
                          style={{ width: 130 }}
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
                    <div>
                      <div className="sub-text" style={{ marginBottom: 6 }}>执行星期</div>
                      <Checkbox.Group
                        options={DAY_OPTIONS}
                        value={s.days}
                        onChange={(v) => updateDays(i, (Array.isArray(v) ? v : []).map(Number))}
                        direction="horizontal"
                      />
                      <div className="sub-text" style={{ marginTop: 6 }}>此处不勾选即代表每天执行</div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        <Descriptions
          column={1}
          colon="："
          data={[
            {
              label: '最近一次定时巡检',
              value: fmtTime(lastRun),
            },
            {
              label: '下次执行计划',
              value: nextRuns.length
                ? nextRuns.map((r) => `每日 ${r.time}（${dayLabel(r.days)}）${r.next_run_at ? ' → ' + fmtTime(r.next_run_at) : ''}`).join('；')
                : '—',
            },
          ]}
          style={{ margin: '20px 0' }}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button type="primary" icon={<IconSave />} loading={saving} onClick={handleSave}>
            保存并生效
          </Button>
          {schedules.some((s) => !s.time) && <Tag color="orange">存在未填时刻的时间点</Tag>}
        </div>
      </div>
    </div>
  );
}
