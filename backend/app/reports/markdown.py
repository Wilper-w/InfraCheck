"""Markdown report rendering (CONTRACT §4 /reports)."""
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


def render_markdown(db: Session, run: Run) -> str:
    summary = counts(db, run.id)
    envs = per_env(db, run.id)
    details = results_detail(db, run.id)
    now = fmt_local_now()

    lines = [
        f"# InfraCheck 巡检报告",
        "",
        f"- 巡检编号 (Run ID): **{run.id}**",
        f"- 触发方式: {run.trigger}",
        f"- 触发人: {run.triggered_by}",
        f"- 开始时间: {fmt_local(run.started_at)}",
        f"- 结束时间: {fmt_local(run.finished_at)}",
        f"- 状态: {run.status}",
        f"- 生成时间: {now}",
        "",
        "## 结果汇总",
        "",
        "| 状态 | 数量 |",
        "| --- | --- |",
        f"| 正常 (normal) | {summary['normal']} |",
        f"| 异常 (abnormal) | {summary['abnormal']} |",
        f"| 不可达 (unreachable) | {summary['unreachable']} |",
        f"| 检查失败 (failed) | {summary['failed']} |",
        f"| 合计 | {summary['total']} |",
        "",
        "## 按环境汇总",
        "",
        "| 环境 | OS | 合计 | 正常 | 异常 | 不可达 | 检查失败 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in envs:
        lines.append(
            f"| {e['environment']} | {e['os_flavor']} | {e['total']} | "
            f"{e['normal']} | {e['abnormal']} | {e['unreachable']} | {e['failed']} |"
        )
    lines += ["", "## 结果明细", "", "| 对象类型 | 对象 | OS | 状态 | 证据 |", "| --- | --- | --- | --- | --- |"]
    for d in details:
        ev = evidence_summary(d["evidence"]).replace("|", "\\|")
        lines.append(
            f"| {d['object_type']} | {d['object_name']} | {d['os_flavor']} | "
            f"{STATUS_LABEL.get(d['status'], d['status'])} | {ev} |"
        )
    lines.append("")
    return "\n".join(lines)
