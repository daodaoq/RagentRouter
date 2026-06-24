"""Real traffic monitoring — reads CC Switch proxy_request_logs.

All data comes from actual Claude Code usage tracked by CC Switch.
No mock/demo data. Costs are calculated from model pricing × token counts.
"""

import os
import sqlite3
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/traffic", tags=["Traffic"])

CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")


def _get_db():
    if not os.path.exists(CCSWITCH_DB):
        return None
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _to_timestamp(raw: int) -> datetime:
    """CC Switch uses JavaScript milliseconds; also handle second-based timestamps."""
    if raw > 10_000_000_000_000:
        return datetime.fromtimestamp(raw / 1000, tz=timezone.utc)
    if raw > 1_000_000_000:
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    # Fallback: small values treated as seconds
    return datetime.fromtimestamp(raw, tz=timezone.utc)


def _calc_cost(model: str, input_tokens: int, output_tokens: int, pricing: dict) -> float:
    """Calculate real cost from token counts and model pricing."""
    rates = pricing.get(model, {})
    in_rate = rates.get("input", 0.0)
    out_rate = rates.get("output", 0.0)
    return round((input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate, 6)


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("/overview")
def traffic_overview():
    """Overall traffic stats: total requests, tokens, cost, this month."""
    conn = _get_db()
    if not conn:
        return {"available": False}

    # Load pricing
    pricing = {}
    for r in conn.execute("SELECT model_id, input_cost_per_million, output_cost_per_million FROM model_pricing").fetchall():
        try:
            pricing[r["model_id"]] = {
                "input": float(r["input_cost_per_million"]),
                "output": float(r["output_cost_per_million"]),
            }
        except (ValueError, TypeError):
            pass

    # Total stats
    total = conn.execute(
        "SELECT COUNT(*) as cnt, "
        "SUM(input_tokens) as it, SUM(output_tokens) as ot "
        "FROM proxy_request_logs"
    ).fetchone()

    # This month
    now = datetime.now(timezone.utc)
    month_start_ms = int(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    month = conn.execute(
        "SELECT COUNT(*) as cnt, SUM(input_tokens) as it, SUM(output_tokens) as ot "
        "FROM proxy_request_logs WHERE created_at >= ?",
        (month_start_ms,),
    ).fetchone()

    # Today
    today_start_ms = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    today = conn.execute(
        "SELECT COUNT(*) as cnt, SUM(input_tokens) as it, SUM(output_tokens) as ot "
        "FROM proxy_request_logs WHERE created_at >= ?",
        (today_start_ms,),
    ).fetchone()

    # Calculate costs by iterating (SQL can't call Python)
    def get_model_rows(extra_where=""):
        q = f"SELECT model, SUM(input_tokens) as it, SUM(output_tokens) as ot FROM proxy_request_logs {extra_where} GROUP BY model"
        return conn.execute(q).fetchall()

    def sum_cost(rows):
        return sum(_calc_cost(r["model"], r["it"] or 0, r["ot"] or 0, pricing) for r in rows)

    total_rows = get_model_rows()
    today_rows = get_model_rows("WHERE created_at >= " + str(today_start_ms))
    month_rows = get_model_rows("WHERE created_at >= " + str(month_start_ms))

    conn.close()

    return {
        "available": True,
        "total": {
            "requests": total["cnt"] or 0,
            "input_tokens": total["it"] or 0,
            "output_tokens": total["ot"] or 0,
            "cost_usd": round(sum_cost(total_rows), 4),
        },
        "today": {
            "requests": today["cnt"] or 0,
            "input_tokens": today["it"] or 0,
            "output_tokens": today["ot"] or 0,
            "cost_usd": round(sum_cost(today_rows), 4),
        },
        "month": {
            "requests": month["cnt"] or 0,
            "input_tokens": month["it"] or 0,
            "output_tokens": month["ot"] or 0,
            "cost_usd": round(sum_cost(month_rows), 4),
        },
    }


@router.get("/by-model")
def traffic_by_model():
    """Breakdown by model."""
    conn = _get_db()
    if not conn:
        return {"available": False, "items": []}

    pricing = {}
    for r in conn.execute("SELECT model_id, input_cost_per_million, output_cost_per_million FROM model_pricing").fetchall():
        try:
            pricing[r["model_id"]] = {
                "input": float(r["input_cost_per_million"]),
                "output": float(r["output_cost_per_million"]),
            }
        except (ValueError, TypeError):
            pass

    rows = conn.execute(
        "SELECT model, COUNT(*) as cnt, SUM(input_tokens) as it, SUM(output_tokens) as ot "
        "FROM proxy_request_logs GROUP BY model ORDER BY cnt DESC"
    ).fetchall()

    items = []
    for r in rows:
        cost = _calc_cost(r["model"], r["it"] or 0, r["ot"] or 0, pricing)
        items.append({
            "model": r["model"],
            "requests": r["cnt"],
            "input_tokens": r["it"] or 0,
            "output_tokens": r["ot"] or 0,
            "cost_usd": round(cost, 6),
        })

    conn.close()
    return {"available": True, "items": items}


@router.get("/recent")
def traffic_recent(limit: int = Query(default=20, le=100)):
    """Latest requests with cost calculated."""
    conn = _get_db()
    if not conn:
        return {"available": False, "items": []}

    pricing = {}
    for r in conn.execute("SELECT model_id, input_cost_per_million, output_cost_per_million FROM model_pricing").fetchall():
        try:
            pricing[r["model_id"]] = {
                "input": float(r["input_cost_per_million"]),
                "output": float(r["output_cost_per_million"]),
            }
        except (ValueError, TypeError):
            pass

    rows = conn.execute(
        "SELECT created_at, model, input_tokens, output_tokens, status_code, latency_ms "
        "FROM proxy_request_logs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()

    items = []
    for r in rows:
        cost = _calc_cost(r["model"], r["input_tokens"] or 0, r["output_tokens"] or 0, pricing)
        try:
            ts = _to_timestamp(r["created_at"])
        except Exception:
            ts = None
        items.append({
            "time": ts.isoformat() if ts else "unknown",
            "model": r["model"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cost_usd": round(cost, 6),
            "status_code": r["status_code"],
            "latency_ms": r["latency_ms"],
        })

    conn.close()
    return {"available": True, "items": items}


@router.get("/daily-trend")
def daily_trend(days: int = Query(default=14, le=90)):
    """Daily token/cost trend."""
    conn = _get_db()
    if not conn:
        return {"available": False, "points": []}

    pricing = {}
    for r in conn.execute("SELECT model_id, input_cost_per_million, output_cost_per_million FROM model_pricing").fetchall():
        try:
            pricing[r["model_id"]] = {
                "input": float(r["input_cost_per_million"]),
                "output": float(r["output_cost_per_million"]),
            }
        except (ValueError, TypeError):
            pass

    rows = conn.execute(
        "SELECT created_at, model, input_tokens, output_tokens FROM proxy_request_logs "
        "ORDER BY created_at ASC"
    ).fetchall()

    # Aggregate by day
    daily: dict[str, dict] = {}
    for r in rows:
        try:
            ts = _to_timestamp(r["created_at"])
        except Exception:
            continue
        day = ts.strftime("%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        daily[day]["requests"] += 1
        daily[day]["input_tokens"] += r["input_tokens"] or 0
        daily[day]["output_tokens"] += r["output_tokens"] or 0
        daily[day]["cost_usd"] += _calc_cost(r["model"], r["input_tokens"] or 0, r["output_tokens"] or 0, pricing)

    # Sort and limit
    sorted_days = sorted(daily.values(), key=lambda d: d["date"])[-days:]
    for d in sorted_days:
        d["cost_usd"] = round(d["cost_usd"], 6)

    conn.close()
    return {"available": True, "points": sorted_days}


@router.get("/status")
def traffic_status():
    """Check if CC Switch traffic data is available."""
    exists = os.path.exists(CCSWITCH_DB)
    count = 0
    if exists:
        conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
        count = conn.execute("SELECT COUNT(*) FROM proxy_request_logs").fetchone()[0]
        conn.close()
    return {"available": exists and count > 0, "total_records": count}
