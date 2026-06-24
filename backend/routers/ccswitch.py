"""CC Switch integration — display and switch providers.

Switching works by:
1. Updating CC Switch's DB + settings.json
2. Restarting CC Switch so it picks up the new config
"""

import json
import os
import sqlite3
import subprocess
import time

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/ccswitch", tags=["CC Switch"])

# CC Switch paths
CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")
CCSWITCH_SETTINGS = os.path.expanduser(r"~\.cc-switch\settings.json")
CCSWITCH_EXE = r"D:\ccswitch\cc-switch.exe"


def _get_ccswitch_db(readonly=True):
    if not os.path.exists(CCSWITCH_DB):
        return None
    mode = "ro" if readonly else "rw"
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _restart_ccswitch():
    """Kill and restart CC Switch so it picks up config changes."""
    # Kill existing process
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "cc-switch.exe"],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass

    # Wait for process to fully exit
    time.sleep(2)

    # Restart
    if os.path.exists(CCSWITCH_EXE):
        subprocess.Popen(
            [CCSWITCH_EXE],
            cwd=os.path.dirname(CCSWITCH_EXE),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    return False


# ── Read endpoints ──────────────────────────────────────────────────


@router.get("/providers")
def list_providers():
    conn = _get_ccswitch_db()
    if not conn:
        return {"items": [], "source": "not_found", "path": CCSWITCH_DB}

    try:
        providers = conn.execute(
            "SELECT id, app_type, name, category, provider_type, is_current, "
            "in_failover_queue, cost_multiplier, limit_daily_usd, limit_monthly_usd, "
            "icon_color, notes "
            "FROM providers "
            "WHERE name != 'default' "
            "ORDER BY CASE WHEN category = 'cn_official' THEN 0 ELSE 1 END, "
            "is_current DESC, name ASC"
        ).fetchall()

        endpoints = conn.execute(
            "SELECT provider_id, app_type, url FROM provider_endpoints"
        ).fetchall()

        ep_map = {}
        for ep in endpoints:
            pid = ep["provider_id"]
            ep_map.setdefault(pid, []).append({"app_type": ep["app_type"], "url": ep["url"]})

        items = []
        for p in providers:
            item = dict(p)
            item["is_current"] = bool(item["is_current"])
            item["endpoints"] = ep_map.get(p["id"], [])
            items.append(item)

        return {"items": items, "source": CCSWITCH_DB, "total": len(items)}
    finally:
        conn.close()


@router.get("/providers/{provider_id}")
def get_provider(provider_id: str):
    conn = _get_ccswitch_db()
    if not conn:
        return {"error": "CC Switch database not found"}

    try:
        p = conn.execute(
            "SELECT id, app_type, name, category, is_current, cost_multiplier, "
            "icon_color FROM providers WHERE id = ?", (provider_id,)
        ).fetchone()
        if not p:
            raise HTTPException(404, "Provider not found")

        eps = conn.execute(
            "SELECT app_type, url FROM provider_endpoints WHERE provider_id = ?",
            (provider_id,),
        ).fetchall()

        result = dict(p)
        result["is_current"] = bool(result["is_current"])
        result["endpoints"] = [{"app_type": e["app_type"], "url": e["url"]} for e in eps]
        return result
    finally:
        conn.close()


@router.get("/status")
def ccswitch_status():
    exists = os.path.exists(CCSWITCH_DB)
    return {
        "available": exists,
        "path": CCSWITCH_DB,
        "exe_path": CCSWITCH_EXE,
        "exe_exists": os.path.exists(CCSWITCH_EXE),
        "db_size_mb": round(os.path.getsize(CCSWITCH_DB) / (1024 * 1024), 2) if exists else 0,
    }


# ── Activate (write + restart) ──────────────────────────────────────


@router.post("/activate/{provider_id}")
def activate_provider(provider_id: str):
    """Switch Claude Code's active API provider.

    Writes to CC Switch config, then restarts CC Switch to apply.
    """
    if not os.path.exists(CCSWITCH_DB):
        raise HTTPException(404, "CC Switch database not found")
    if not os.path.exists(CCSWITCH_SETTINGS):
        raise HTTPException(404, "CC Switch settings not found")
    if not os.path.exists(CCSWITCH_EXE):
        raise HTTPException(500, f"CC Switch executable not found at {CCSWITCH_EXE}")

    # 1. Verify provider exists
    ro_conn = _get_ccswitch_db(readonly=True)
    try:
        provider = ro_conn.execute(
            "SELECT id, name, app_type FROM providers WHERE id = ? AND name != 'default'",
            (provider_id,),
        ).fetchone()
        if not provider:
            raise HTTPException(404, f"Provider '{provider_id}' not found")
    finally:
        ro_conn.close()

    # 2. Update providers table
    rw_conn = _get_ccswitch_db(readonly=False)
    try:
        rw_conn.execute(
            "UPDATE providers SET is_current = 0 WHERE app_type = ?",
            (provider["app_type"],),
        )
        rw_conn.execute(
            "UPDATE providers SET is_current = 1 WHERE id = ?",
            (provider_id,),
        )
        rw_conn.commit()
    finally:
        rw_conn.close()

    # 3. Update settings.json
    with open(CCSWITCH_SETTINGS, "r", encoding="utf-8") as f:
        settings = json.load(f)
    settings["currentProviderClaude"] = provider_id
    with open(CCSWITCH_SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    # 4. Restart CC Switch to apply
    restarted = _restart_ccswitch()

    return {
        "success": True,
        "provider_id": provider_id,
        "provider_name": provider["name"],
        "restarted": restarted,
        "message": f"Switched to '{provider['name']}'. CC Switch has been restarted to apply changes.",
    }
