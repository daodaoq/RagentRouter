"""Monitoring endpoints — observe every Claude Code request through RAgent Router.

Reads from RAgent Router's own request_logs table (written by proxy_router.py).
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func

from database import SessionLocal
from models import RequestLog

router = APIRouter(prefix="/api/monitor", tags=["Monitor"])
LOCAL_TZ = timezone(timedelta(hours=8))


def _row_to_dict(r: RequestLog) -> dict:
    return {
        "id": r.id,
        "created_at": r.created_at.replace(tzinfo=timezone.utc)
            .astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
        "prompt": r.prompt or "",
        "prompt_tokens": r.prompt_tokens or 0,
        "completion_tokens": r.completion_tokens or 0,
        "cache_read_tokens": r.cache_read_tokens or 0,
        "cache_creation_tokens": r.cache_creation_tokens or 0,
        "total_tokens": r.total_tokens or 0,
        "model": r.model,
        "provider": r.provider,
        "provider_id": r.provider_id,
        "upstream_url": r.upstream_url,
        "route_reason": r.route_reason,
        "intent_match": r.intent_match,
        "intent_score": r.intent_score,
        "status": r.status,
        "error_detail": r.error_detail,
        "upstream_request_id": r.upstream_request_id,
        "cost_usd": r.cost_usd or 0.0,
        "latency_ms": r.latency_ms or 0,
    }


@router.get("/recent")
def monitor_recent(
    limit: int = Query(default=50, le=500),
    provider: str | None = None,
    intent: str | None = None,
):
    """Recent request log, newest first. Optional filters by provider/intent."""
    db = SessionLocal()
    try:
        q = db.query(RequestLog).order_by(RequestLog.created_at.desc())
        if provider:
            q = q.filter(RequestLog.provider == provider)
        if intent:
            q = q.filter(RequestLog.intent_match == intent)
        rows = q.limit(limit).all()
        return {"items": [_row_to_dict(r) for r in rows]}
    finally:
        db.close()


@router.get("/overview")
def monitor_overview():
    """Aggregate stats — total, today, by provider, by model."""
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        today_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        total = db.query(RequestLog).count()
        today = db.query(RequestLog).filter(RequestLog.created_at >= today_utc).count()
        errors = db.query(RequestLog).filter(RequestLog.status != "ok").count()

        # Totals
        agg = db.query(
            func.sum(RequestLog.prompt_tokens),
            func.sum(RequestLog.completion_tokens),
            func.sum(RequestLog.total_tokens),
            func.sum(RequestLog.cost_usd),
            func.sum(RequestLog.latency_ms),
        ).first()
        sum_in = agg[0] or 0
        sum_out = agg[1] or 0
        sum_tokens = agg[2] or 0
        sum_cost = float(agg[3] or 0)
        sum_latency = int(agg[4] or 0)
        avg_latency = int(sum_latency / total) if total > 0 else 0

        # By provider
        provider_rows = db.query(
            RequestLog.provider,
            func.count(RequestLog.id).label("cnt"),
            func.sum(RequestLog.prompt_tokens).label("in_t"),
            func.sum(RequestLog.completion_tokens).label("out_t"),
            func.sum(RequestLog.cost_usd).label("cost"),
        ).group_by(RequestLog.provider).all()

        by_provider = [
            {
                "provider": r.provider,
                "requests": r.cnt,
                "input_tokens": int(r.in_t or 0),
                "output_tokens": int(r.out_t or 0),
                "cost_usd": round(float(r.cost or 0), 4),
            }
            for r in provider_rows
        ]

        # By model
        model_rows = db.query(
            RequestLog.model,
            func.count(RequestLog.id).label("cnt"),
            func.sum(RequestLog.total_tokens).label("model_tokens"),
            func.sum(RequestLog.cost_usd).label("model_cost"),
            func.avg(RequestLog.latency_ms).label("model_avg_ms"),
        ).group_by(RequestLog.model).all()

        by_model = [
            {
                "model": r.model,
                "requests": r.cnt,
                "total_tokens": int(r.model_tokens or 0),
                "cost_usd": round(float(r.model_cost or 0), 4),
                "avg_latency_ms": int(r.model_avg_ms or 0),
            }
            for r in model_rows
        ]

        # By intent
        intent_rows = db.query(
            RequestLog.intent_match,
            func.count(RequestLog.id).label("cnt"),
            func.sum(RequestLog.cost_usd).label("cost"),
        ).filter(RequestLog.intent_match != "").group_by(RequestLog.intent_match).all()

        by_intent = [
            {
                "intent": r.intent_match,
                "requests": r.cnt,
                "cost_usd": round(float(r.cost or 0), 4),
            }
            for r in intent_rows
        ]

        return {
            "total_requests": total,
            "today_requests": today,
            "error_count": errors,
            "error_rate": round(errors / total * 100, 2) if total > 0 else 0,
            "total_input_tokens": int(sum_in),
            "total_output_tokens": int(sum_out),
            "total_tokens": int(sum_tokens),
            "total_cost_usd": round(sum_cost, 4),
            "avg_latency_ms": avg_latency,
            "by_provider": by_provider,
            "by_model": by_model,
            "by_intent": by_intent,
        }
    finally:
        db.close()


@router.get("/timeline")
def monitor_timeline(hours: int = Query(default=24, le=168)):
    """Hourly timeline — requests and cost over the last N hours."""
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = db.query(
            func.strftime("%Y-%m-%d %H:00", RequestLog.created_at).label("hour"),
            RequestLog.provider,
            func.count(RequestLog.id).label("cnt"),
            func.sum(RequestLog.cost_usd).label("cost"),
        ).filter(RequestLog.created_at >= since).group_by("hour", RequestLog.provider).all()

        # Pivot into hour → providers dict
        by_hour: dict = {}
        for r in rows:
            by_hour.setdefault(r.hour, {"hour": r.hour, "requests": 0, "cost": 0.0, "providers": {}})
            by_hour[r.hour]["requests"] += r.cnt
            by_hour[r.hour]["cost"] += float(r.cost or 0)
            by_hour[r.hour]["providers"][r.provider] = by_hour[r.hour]["providers"].get(r.provider, 0) + r.cnt

        points = sorted(by_hour.values(), key=lambda x: x["hour"])
        for p in points:
            p["cost"] = round(p["cost"], 4)
        return {"hours": hours, "points": points}
    finally:
        db.close()


@router.get("/by-model")
def monitor_by_model():
    """Detailed per-model stats."""
    db = SessionLocal()
    try:
        rows = db.query(
            RequestLog.model,
            RequestLog.provider,
            func.count(RequestLog.id).label("cnt"),
            func.sum(RequestLog.prompt_tokens).label("sum_in"),
            func.sum(RequestLog.completion_tokens).label("sum_out"),
            func.sum(RequestLog.cache_read_tokens).label("sum_cache"),
            func.sum(RequestLog.cost_usd).label("sum_cost"),
            func.avg(RequestLog.latency_ms).label("avg_lat"),
            func.min(RequestLog.latency_ms).label("min_lat"),
            func.max(RequestLog.latency_ms).label("max_lat"),
        ).group_by(RequestLog.model, RequestLog.provider).all()

        return {
            "items": [
                {
                    "model": r.model,
                    "provider": r.provider,
                    "requests": r.cnt,
                    "input_tokens": int(r.sum_in or 0),
                    "output_tokens": int(r.sum_out or 0),
                    "cache_read_tokens": int(r.sum_cache or 0),
                    "cost_usd": round(float(r.sum_cost or 0), 4),
                    "avg_latency_ms": int(r.avg_lat or 0),
                    "min_latency_ms": int(r.min_lat or 0),
                    "max_latency_ms": int(r.max_lat or 0),
                }
                for r in rows
            ]
        }
    finally:
        db.close()


@router.get("/status")
def monitor_status():
    """Monitor system health — total records, last request, table exists."""
    db = SessionLocal()
    try:
        total = db.query(RequestLog).count()
        last = db.query(RequestLog).order_by(RequestLog.created_at.desc()).first()
        last_ts = None
        if last and last.created_at:
            last_ts = last.created_at.replace(tzinfo=timezone.utc)\
                .astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "available": total > 0,
            "total_records": total,
            "last_request": last_ts,
        }
    finally:
        db.close()
