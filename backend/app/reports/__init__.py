"""Report rendering: HTML + Markdown (CONTRACT §4 /reports, §6)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import config
from app.models import CheckResult, Environment, Report, Run

STATUS_LABEL = {
    "normal": "正常",
    "abnormal": "异常",
    "unreachable": "不可达",
    "failed": "检查失败",
}


def _counts(db: Session, run_id: int) -> dict[str, int]:
    rows = (
        db.query(CheckResult.status, func.count(CheckResult.id))
        .filter(CheckResult.run_id == run_id)
        .group_by(CheckResult.status)
        .all()
    )
    counts = {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0}
    for status, n in rows:
        counts[status] = n
    counts["total"] = sum(counts.values())
    return counts


def _per_env(db: Session, run_id: int) -> list[dict]:
    envs = db.query(Environment).order_by(Environment.id).all()
    out = []
    for env in envs:
        rows = db.query(CheckResult).filter(
            CheckResult.run_id == run_id, CheckResult.environment_id == env.id
        ).all()
        c = {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0}
        for r in rows:
            c[r.status] = c.get(r.status, 0) + 1
        out.append(
            {
                "environment": env.name,
                "os_flavor": env.os_flavor,
                "total": len(rows),
                **c,
            }
        )
    return out


def _results_detail(db: Session, run_id: int) -> list[dict]:
    rows = (
        db.query(CheckResult)
        .filter(CheckResult.run_id == run_id)
        .order_by(CheckResult.environment_id, CheckResult.id)
        .all()
    )
    return [
        {
            "object_type": r.object_type,
            "object_name": r.object_name,
            "status": r.status,
            "evidence": r.evidence,
            "os_flavor": r.os_flavor or "all",
        }
        for r in rows
    ]


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_markdown(db: Session, run: Run) -> str:
    counts = _counts(db, run.id)
    per_env = _per_env(db, run.id)
    details = _results_detail(db, run.id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"# InfraCheck 巡检报告",
        "",
        f"- 巡检编号 (Run ID): **{run.id}**",
        f"- 触发方式: {run.trigger}",
        f"- 触发人: {run.triggered_by}",
        f"- 开始时间: {run.started_at}",
        f"- 结束时间: {run.finished_at or '-'}",
        f"- 状态: {run.status}",
        f"- 生成时间: {now}",
        "",
        "## 结果汇总",
        "",
        "| 状态 | 数量 |",
        "| --- | --- |",
        f"| 正常 (normal) | {counts['normal']} |",
        f"| 异常 (abnormal) | {counts['abnormal']} |",
        f"| 不可达 (unreachable) | {counts['unreachable']} |",
        f"| 检查失败 (failed) | {counts['failed']} |",
        f"| 合计 | {counts['total']} |",
        "",
        "## 按环境汇总",
        "",
        "| 环境 | OS | 合计 | 正常 | 异常 | 不可达 | 检查失败 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in per_env:
        lines.append(
            f"| {e['environment']} | {e['os_flavor']} | {e['total']} | "
            f"{e['normal']} | {e['abnormal']} | {e['unreachable']} | {e['failed']} |"
        )
    lines += ["", "## 结果明细", "", "| 对象类型 | 对象 | OS | 状态 | 证据 |", "| --- | --- | --- | --- | --- |"]
    for d in details:
        ev = d["evidence"].replace("|", "\\|").replace("\n", " ")[:200]
        lines.append(
            f"| {d['object_type']} | {d['object_name']} | {d['os_flavor']} | "
            f"{STATUS_LABEL.get(d['status'], d['status'])} | {ev} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_html(db: Session, run: Run) -> str:
    counts = _counts(db, run.id)
    per_env = _per_env(db, run.id)
    details = _results_detail(db, run.id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    summary_cells = "".join(
        f'<div class="cell"><div class="num {s}">{counts[s]}</div><div class="lbl">{STATUS_LABEL[s]}</div></div>'
        for s in ("normal", "abnormal", "unreachable", "failed")
    )
    env_rows = "".join(
        "<tr>"
        f"<td>{_escape(e['environment'])}</td><td>{_escape(e['os_flavor'])}</td>"
        f"<td>{e['total']}</td><td>{e['normal']}</td><td>{e['abnormal']}</td>"
        f"<td>{e['unreachable']}</td><td>{e['failed']}</td>"
        "</tr>"
        for e in per_env
    )
    detail_rows = "".join(
        "<tr>"
        f"<td>{_escape(d['object_type'])}</td><td>{_escape(d['object_name'])}</td>"
        f"<td>{_escape(d['os_flavor'])}</td>"
        f"<td class='st {d['status']}'>{STATUS_LABEL.get(d['status'], d['status'])}</td>"
        f"<td>{_escape(d['evidence'])}</td>"
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
开始: {run.started_at} · 结束: {run.finished_at or '-'} · 状态: {run.status} · 生成: {now}
</div>
<h2>结果汇总 (合计 {counts['total']})</h2>
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


def generate_report(db: Session, run: Run, account: str) -> Report:
    md = render_markdown(db, run)
    html = render_html(db, run)
    out_dir = config.REPORTS_OUT_DIR
    md_path = out_dir / f"run-{run.id}.md"
    html_path = out_dir / f"run-{run.id}.html"
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return Report(
        run_id=run.id,
        rendered_by=account,
        generated_at=datetime.now(timezone.utc),
        html_path=str(html_path),
        md_path=str(md_path),
    )
