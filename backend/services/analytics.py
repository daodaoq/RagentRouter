from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import RequestLog
from services.provider_adapter import COST_RATES


def log_request(
    db: Session,
    *,
    prompt: str,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
    provider: str,
    route_reason: str,
    latency_ms: int,
) -> RequestLog:
    """Record a routed request for analytics."""
    total_tokens = prompt_tokens + completion_tokens
    rates = COST_RATES.get(provider, {"input": 0, "output": 0})
    cost = round(
        (prompt_tokens / 1_000_000) * rates["input"]
        + (completion_tokens / 1_000_000) * rates["output"],
        6,
    )

    log = RequestLog(
        id=uuid.uuid4().hex[:12],
        prompt=prompt[:500],  # Truncate for storage
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
        provider=provider,
        route_reason=route_reason,
        cost_usd=cost,
        latency_ms=latency_ms,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_cost_overview(db: Session) -> dict:
    """Today's cost, monthly cost, savings estimate."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    today_cost = (
        db.query(func.coalesce(func.sum(RequestLog.cost_usd), 0))
        .filter(RequestLog.created_at >= today_start)
        .scalar()
    )

    month_cost = (
        db.query(func.coalesce(func.sum(RequestLog.cost_usd), 0))
        .filter(RequestLog.created_at >= month_start)
        .scalar()
    )

    total_requests = db.query(func.count(RequestLog.id)).scalar() or 0

    # Savings estimate: if all requests went to Claude (most expensive)
    # Actual cost already recorded. This is a simplified estimate.
    claude_output_rate = COST_RATES["claude"]["output"]
    total_tokens_all = (
        db.query(func.coalesce(func.sum(RequestLog.total_tokens), 0)).scalar() or 0
    )
    estimated_claude_cost = (total_tokens_all / 1_000_000) * claude_output_rate
    saved = round(max(0, estimated_claude_cost - float(month_cost)), 2)
    saving_rate = round((saved / estimated_claude_cost * 100), 1) if estimated_claude_cost > 0 else 0.0

    return {
        "today_cost": round(float(today_cost), 4),
        "month_cost": round(float(month_cost), 4),
        "saved_amount": saved,
        "saving_rate": saving_rate,
        "total_requests": total_requests,
    }


def get_model_distribution(db: Session) -> list[dict]:
    """Model usage distribution."""
    rows = (
        db.query(RequestLog.model, func.count(RequestLog.id).label("cnt"))
        .group_by(RequestLog.model)
        .order_by(func.count(RequestLog.id).desc())
        .all()
    )
    total = sum(r.cnt for r in rows) or 1
    return [
        {
            "model": r.model,
            "count": r.cnt,
            "percentage": round(r.cnt / total * 100, 1),
        }
        for r in rows
    ]


def get_recent_routes(db: Session, limit: int = 20) -> list[dict]:
    """Recent routing decisions."""
    logs = (
        db.query(RequestLog)
        .order_by(RequestLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "prompt": log.prompt[:100],
            "model": log.model,
            "provider": log.provider,
            "route_reason": log.route_reason,
            "cost_usd": log.cost_usd,
            "latency_ms": log.latency_ms,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


def get_cost_trend(db: Session, days: int = 7) -> list[dict]:
    """Daily cost trend for the last N days."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    points = []
    for i in range(days - 1, -1, -1):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_cost = (
            db.query(func.coalesce(func.sum(RequestLog.cost_usd), 0))
            .filter(RequestLog.created_at >= day_start, RequestLog.created_at < day_end)
            .scalar()
        )
        day_requests = (
            db.query(func.count(RequestLog.id))
            .filter(RequestLog.created_at >= day_start, RequestLog.created_at < day_end)
            .scalar()
        )
        points.append({
            "date": day_start.strftime("%m-%d"),
            "cost": round(float(day_cost), 4),
            "requests": day_requests or 0,
        })
    return points
