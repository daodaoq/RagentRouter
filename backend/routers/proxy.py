"""Instant provider switching — RAgent Router's own state, no restart needed."""

import logging
import os
import sqlite3

from fastapi import APIRouter, HTTPException

from services.provider_state import get_active_provider_id, set_active_provider_id

router = APIRouter(prefix="/api/proxy", tags=["Proxy"])

CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")

log = logging.getLogger("ragent")


def _get_db():
    if not os.path.exists(CCSWITCH_DB):
        return None
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/current")
def get_current():
    """Get the currently active provider."""
    active_id = get_active_provider_id()

    conn = _get_db()
    name = active_id
    endpoints = []
    if conn:
        try:
            row = conn.execute(
                "SELECT id, name, icon_color FROM providers WHERE id = ?", (active_id,)
            ).fetchone()
            if row:
                name = row["name"]
            eps = conn.execute(
                "SELECT app_type, url FROM provider_endpoints WHERE provider_id = ?",
                (active_id,),
            ).fetchall()
            endpoints = [{"app_type": e["app_type"], "url": e["url"]} for e in eps]
        finally:
            conn.close()

    return {
        "provider_id": active_id,
        "provider_name": name,
        "endpoints": endpoints,
    }


@router.post("/activate/{provider_id}")
def activate(provider_id: str):
    """Switch to a different provider — instant, no restart needed."""
    conn = _get_db()
    if not conn:
        raise HTTPException(500, "CC Switch database not found")

    try:
        row = conn.execute(
            "SELECT id, name, settings_config FROM providers WHERE id = ? AND name != 'default'",
            (provider_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Provider '{provider_id}' not found")

        if not row["settings_config"]:
            raise HTTPException(400, f"Provider '{row['name']}' has no API configuration")

        set_active_provider_id(provider_id)

        log.info("SWITCH | %s → %s", row["name"], provider_id[:12])

        return {
            "success": True,
            "provider_id": provider_id,
            "provider_name": row["name"],
            "message": f"Now using '{row['name']}' — all future requests go to this provider.",
        }
    finally:
        conn.close()
