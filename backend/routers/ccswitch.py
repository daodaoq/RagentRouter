"""Read CC Switch local database and control active provider."""

import json
import sqlite3
import os

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/ccswitch", tags=["CC Switch"])

# CC Switch paths
CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")
CCSWITCH_SETTINGS = os.path.expanduser(r"~\.cc-switch\settings.json")


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


@router.post("/activate/{provider_id}")
def activate_provider(provider_id: str):
    """Set a provider as the active one for Claude in CC Switch.

    This updates both settings.json (currentProviderClaude) and
    the providers table (is_current flag) in CC Switch.
    """
    if not os.path.exists(CCSWITCH_DB):
        raise HTTPException(404, "CC Switch database not found")
    if not os.path.exists(CCSWITCH_SETTINGS):
        raise HTTPException(404, "CC Switch settings not found")

    # 1. Verify the provider exists and get its info
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        provider = conn.execute(
            "SELECT id, name, app_type FROM providers WHERE id = ? AND name != 'default'",
            (provider_id,),
        ).fetchone()
        if not provider:
            raise HTTPException(404, f"Provider '{provider_id}' not found or is system default")

        # 2. Unset all current providers of the same app_type
        conn.execute(
            "UPDATE providers SET is_current = 0 WHERE app_type = ?",
            (provider["app_type"],),
        )
        # 3. Set the new one as current
        conn.execute(
            "UPDATE providers SET is_current = 1 WHERE id = ?",
            (provider_id,),
        )
        conn.commit()

        # 4. Update settings.json
        with open(CCSWITCH_SETTINGS, "r", encoding="utf-8") as f:
            settings = json.load(f)

        settings["currentProviderClaude"] = provider_id

        with open(CCSWITCH_SETTINGS, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "provider_id": provider_id,
            "provider_name": provider["name"],
            "app_type": provider["app_type"],
            "message": f"Activated '{provider['name']}' for {provider['app_type']}",
            "note": "CC Switch may need to restart for changes to take effect",
        }
    finally:
        conn.close()
