"""Real traffic monitoring — reads CC Switch proxy_request_logs.

All data from actual Claude Code usage via CC Switch.
Uses CC Switch's own cost columns for accuracy.
Timestamps are Unix seconds, queried in local time (UTC+8).
"""

import os
import sqlite3
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/traffic", tags=["Traffic"])

CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")
LOCAL_TZ = timezone(timedelta(hours=8))  # UTC+8


def _get_db():
    if not os.path.exists(CCSWITCH_DB):
        return None
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _to_timestamp(raw: int) -> datetime:
    return datetime.fromtimestamp(raw, tz=timezone.utc)


def _local_now() -> datetime:
    return datetime.now(LOCAL_TZ)


def _start_of_day(dt: datetime) -> int:
    """Unix seconds for start of day in local time."""
    local_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(local_start.timestamp())


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("/overview")
def traffic_overview():
    conn = _get_db()
    if not conn:
        return {"available": False}

    now = _local_now()
    today_start = _start_of_day(now)
    month_start = _start_of_day(now.replace(day=1))

    def stats(where=""):
        where_clause = f"WHERE {where}" if where else ""
        return conn.execute(f"""
            SELECT
                COUNT(*) as cnt,
                SUM(input_tokens) as it,
                SUM(output_tokens) as ot,
                SUM(cache_read_tokens) as crt,
                SUM(cache_creation_tokens) as cct,
                SUM(CAST(total_cost_usd AS REAL)) as tc
            FROM proxy_request_logs
            {where_clause}
        """).fetchone()

    total = stats()
    today = stats(f"created_at >= {today_start}")
    month = stats(f"created_at >= {month_start}")

    conn.close()

    return {
        "available": True,
        "total": {
            "requests": total["cnt"] or 0,
            "input_tokens": total["it"] or 0,
            "output_tokens": total["ot"] or 0,
            "cache_read_tokens": total["crt"] or 0,
            "cost_usd": round(total["tc"] or 0, 4),
        },
        "today": {
            "requests": today["cnt"] or 0,
            "input_tokens": today["it"] or 0,
            "output_tokens": today["ot"] or 0,
            "cache_read_tokens": today["crt"] or 0,
            "cost_usd": round(today["tc"] or 0, 4),
        },
        "month": {
            "requests": month["cnt"] or 0,
            "input_tokens": month["it"] or 0,
            "output_tokens": month["ot"] or 0,
            "cache_read_tokens": month["crt"] or 0,
            "cost_usd": round(month["tc"] or 0, 4),
        },
    }


@router.get("/by-model")
def traffic_by_model():
    conn = _get_db()
    if not conn:
        return {"available": False, "items": []}

    rows = conn.execute("""
        SELECT model,
            COUNT(*) as cnt,
            SUM(input_tokens) as it,
            SUM(output_tokens) as ot,
            SUM(cache_read_tokens) as crt,
            SUM(CAST(total_cost_usd AS REAL)) as tc
        FROM proxy_request_logs
        GROUP BY model ORDER BY cnt DESC
    """).fetchall()

    items = []
    for r in rows:
        items.append({
            "model": r["model"],
            "requests": r["cnt"],
            "input_tokens": r["it"] or 0,
            "output_tokens": r["ot"] or 0,
            "cache_read_tokens": r["crt"] or 0,
            "cost_usd": round(r["tc"] or 0, 4),
        })

    conn.close()
    return {"available": True, "items": items}


@router.get("/recent")
def traffic_recent(limit: int = Query(default=20, le=100)):
    conn = _get_db()
    if not conn:
        return {"available": False, "items": []}

    rows = conn.execute("""
        SELECT created_at, model, input_tokens, output_tokens,
               cache_read_tokens, CAST(total_cost_usd AS REAL) as tc,
               status_code, latency_ms
        FROM proxy_request_logs
        ORDER BY created_at DESC LIMIT ?
    """, (limit,)).fetchall()

    items = []
    for r in rows:
        try:
            ts = _to_timestamp(r["created_at"])
            ts_str = ts.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts_str = "unknown"
        items.append({
            "time": ts_str,
            "model": r["model"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cache_read_tokens": r["cache_read_tokens"],
            "cost_usd": round(r["tc"] or 0, 6),
            "status_code": r["status_code"],
            "latency_ms": r["latency_ms"],
        })

    conn.close()
    return {"available": True, "items": items}


@router.get("/daily-trend")
def daily_trend(days: int = Query(default=14, le=90)):
    conn = _get_db()
    if not conn:
        return {"available": False, "points": []}

    rows = conn.execute("""
        SELECT created_at, CAST(total_cost_usd AS REAL) as tc
        FROM proxy_request_logs ORDER BY created_at ASC
    """).fetchall()

    daily: dict[str, dict] = {}
    for r in rows:
        try:
            ts = _to_timestamp(r["created_at"]).astimezone(LOCAL_TZ)
        except Exception:
            continue
        day = ts.strftime("%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "requests": 0, "cost_usd": 0.0}
        daily[day]["requests"] += 1
        daily[day]["cost_usd"] += r["tc"] or 0

    sorted_days = sorted(daily.values(), key=lambda d: d["date"])[-days:]
    for d in sorted_days:
        d["cost_usd"] = round(d["cost_usd"], 4)

    conn.close()
    return {"available": True, "points": sorted_days}


@router.get("/status")
def traffic_status():
    exists = os.path.exists(CCSWITCH_DB)
    count = 0
    if exists:
        conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
        count = conn.execute("SELECT COUNT(*) FROM proxy_request_logs").fetchone()[0]
        conn.close()
    return {"available": exists and count > 0, "total_records": count}
