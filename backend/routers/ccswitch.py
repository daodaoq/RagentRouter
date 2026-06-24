"""Read CC Switch local database to display configured providers and endpoints."""

import json
import sqlite3
import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/ccswitch", tags=["CC Switch"])

# CC Switch database path
CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")


def _get_ccswitch_db():
    """Open a read-only connection to the CC Switch database."""
    if not os.path.exists(CCSWITCH_DB):
        return None
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/providers")
def list_providers():
    """List all providers configured in CC Switch, with endpoints."""
    conn = _get_ccswitch_db()
    if not conn:
        return {"items": [], "source": "not_found", "path": CCSWITCH_DB}

    try:
        providers = conn.execute(
            "SELECT id, app_type, name, category, provider_type, is_current, "
            "in_failover_queue, cost_multiplier, limit_daily_usd, limit_monthly_usd, "
            "icon_color, notes "
            "FROM providers ORDER BY is_current DESC, name ASC"
        ).fetchall()

        endpoints = conn.execute(
            "SELECT provider_id, app_type, url FROM provider_endpoints"
        ).fetchall()

        # Map provider_id → list of endpoint URLs
        ep_map = {}
        for ep in endpoints:
            pid = ep["provider_id"]
            if pid not in ep_map:
                ep_map[pid] = []
            ep_map[pid].append({"app_type": ep["app_type"], "url": ep["url"]})

        items = []
        for p in providers:
            item = dict(p)
            item["is_current"] = bool(item["is_current"])
            item["endpoints"] = ep_map.get(p["id"], [])
            # Don't expose encrypted settings_config
            items.append(item)

        return {"items": items, "source": CCSWITCH_DB, "total": len(items)}
    finally:
        conn.close()


@router.get("/providers/{provider_id}")
def get_provider(provider_id: str):
    """Get a single provider's full details from CC Switch."""
    conn = _get_ccswitch_db()
    if not conn:
        return {"error": "CC Switch database not found", "path": CCSWITCH_DB}

    try:
        p = conn.execute(
            "SELECT id, app_type, name, category, provider_type, is_current, "
            "in_failover_queue, cost_multiplier, limit_daily_usd, limit_monthly_usd, "
            "icon_color, notes "
            "FROM providers WHERE id = ?", (provider_id,)
        ).fetchone()

        if not p:
            return {"error": "Provider not found"}

        endpoints = conn.execute(
            "SELECT app_type, url FROM provider_endpoints WHERE provider_id = ?",
            (provider_id,),
        ).fetchall()

        result = dict(p)
        result["is_current"] = bool(result["is_current"])
        result["endpoints"] = [{"app_type": e["app_type"], "url": e["url"]} for e in endpoints]
        return result
    finally:
        conn.close()


@router.get("/status")
def ccswitch_status():
    """Check whether CC Switch database is accessible."""
    exists = os.path.exists(CCSWITCH_DB)
    return {
        "available": exists,
        "path": CCSWITCH_DB,
        "db_size_mb": round(os.path.getsize(CCSWITCH_DB) / (1024 * 1024), 2) if exists else 0,
    }
