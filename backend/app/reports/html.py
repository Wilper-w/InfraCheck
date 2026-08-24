"""HTML report rendering (CONTRACT §4 /reports)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Run
from app.reports.data import (
    STATUS_LABEL,
    counts,
    evidence_summary,
    fmt_local,
    fmt_local_now,
    per_env,
    results_detail,
)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(db: Session, run: Run) -> str:
    summary = counts(db, run.id)
    envs = per_env(db, run.id)
    details = results_detail(db, run.id)
    now = fmt_local_now()

    summary_cells = "".join(
        f'<div class="cell"><div class="num {s}">{summary[s]}</div><div class="lbl">{STATUS_LABEL[s]}</div></div>'
        for s in ("normal", "abnormal", "unreachable", "failed")
    )
    env_rows = "".join(
        "<tr>"
        f"<td>{_escape(e['environment'])}</td><td>{_escape(e['os_flavor'])}</td>"
        f"<td>{e['total']}</td><td>{e['normal']}</td><td>{e['abnormal']}</td>"
        f"<td>{e['unreachable']}</td><td>{e['failed']}</td>"
        "</tr>"
        for e in envs
    )
    detail_rows = "".join(
        "<tr>"
        f"<td>{_escape(d['object_type'])}</td><td>{_escape(d['object_name'])}</td>"
        f"<td>{_escape(d['os_flavor'])}</td>"
        f"<td class='st {d['status']}'>{STATUS_LABEL.get(d['status'], d['status'])}</td>"
        f"<td>{_escape(evidence_summary(d['evidence']))}</td>"
        "</tr>"
        for d in details
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>InfraCheck 巡检报告 #{run.id}</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;color:#1d2129}}
h1{{color:#165dff}}.meta{{color:#86909c;font-size:13px;margin-bottom:16px}}
.summary{{display:flex;gap:12px;margin:16px 0}}
.cell{{flex:1;background:#f7f8fa;border-radius:6px;padding:12px;text-align:center}}
.num{{font-size:28px;font-weight:700}}.num.normal{{color:#00b42a}}.num.abnormal{{color:#f53f3f}}
.num.unreachable{{color:#ff7d00}}.num.failed{{color:#722ed1}}.lbl{{color:#86909c;font-size:12px}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}}
th,td{{border:1px solid #e5e6eb;padding:6px 8px;text-align:left}}
th{{background:#f7f8fa}}.st.normal{{color:#00b42a}}.st.abnormal{{color:#f53f3f}}
.st.unreachable{{color:#ff7d00}}.st.failed{{color:#722ed1}}
</style></head><body>
<h1>InfraCheck 巡检报告 #{run.id}</h1>
<div class="meta">
触发方式: {run.trigger} · 触发人: {_escape(run.triggered_by)} ·
开始: {fmt_local(run.started_at)} · 结束: {fmt_local(run.finished_at)} · 状态: {run.status} · 生成: {now}
</div>
<h2>结果汇总 (合计 {summary['total']})</h2>
<div class="summary">{summary_cells}</div>
<h2>按环境汇总</h2>
<table><thead><tr>
<th>环境</th><th>OS</th><th>合计</th><th>正常</th><th>异常</th><th>不可达</th><th>检查失败</th>
</tr></thead><tbody>{env_rows}</tbody></table>
<h2>结果明细</h2>
<table><thead><tr>
<th>对象类型</th><th>对象</th><th>OS</th><th>状态</th><th>证据</th>
</tr></thead><tbody>{detail_rows}</tbody></table>
</body></html>"""
