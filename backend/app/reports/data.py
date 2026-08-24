"""Aggregating a run's results into the numbers a report renders."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CheckResult, Environment

STATUS_LABEL = {
    "normal": "正常",
    "abnormal": "异常",
    "unreachable": "不可达",
    "failed": "检查失败",
}

# 证据中 verdict（判定码）的人类可读文案
VERDICT_LABEL = {
    "pass": "通过",
    "threshold_exceeded": "阈值超限",
    "connection_timeout": "连接超时",
    "command_nonzero": "命令执行异常",
    "fail": "检查失败",
    "error": "错误",
}


def evidence_summary(evidence: str) -> str:
    """把一条结构化的 evidence 压缩为一眼可读的摘要。

    evidence 是 JSON 字符串（check/object/verdict/detail/output…）。正常项
    直接展示关键指标；异常项以「判定：原因/阈值」形式突出问题点。无法解析时
    原样降级返回。
    """
    if not evidence:
        return "-"
    try:
        d = json.loads(evidence)
    except (TypeError, ValueError):
        return evidence.strip()[:200]
    detail = (d.get("detail") or d.get("output") or "").strip()
    detail = " ".join(detail.split())[:160]
    verdict = d.get("verdict", "")
    label = VERDICT_LABEL.get(verdict, verdict) or "未知"
    if verdict == "pass":
        return detail or label
    return f"{label}：{detail}" if detail else label


def fmt_local(dt_str: str | None) -> str:
    """Render a naive-UTC stored timestamp in the server's local timezone."""
    if not dt_str:
        return "-"
    try:
        dt = datetime.fromisoformat(str(dt_str))
    except ValueError:
        return str(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # stored as UTC despite naive
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def fmt_local_now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def counts(db: Session, run_id: int) -> dict[str, int]:
    rows = (
        db.query(CheckResult.status, func.count(CheckResult.id))
        .filter(CheckResult.run_id == run_id)
        .group_by(CheckResult.status)
        .all()
    )
    out = {"normal": 0, "abnormal": 0, "unreachable": 0, "failed": 0}
    for status, n in rows:
        out[status] = n
    out["total"] = sum(out.values())
    return out


def per_env(db: Session, run_id: int) -> list[dict]:
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


def results_detail(db: Session, run_id: int) -> list[dict]:
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
