"""First-time setup — configure CC Switch to point to RAgent Router."""

import json
import os
import sqlite3
import uuid

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/setup", tags=["Setup"])

CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")
CCSWITCH_SETTINGS = os.path.expanduser(r"~\.cc-switch\settings.json")
CLAUDE_SETTINGS = os.path.expanduser(r"~\.claude\settings.json")

PROXY_PROVIDER_NAME = "RAgent Proxy"
PROXY_URL = "http://localhost:15722"


def _get_rw_db():
    if not os.path.exists(CCSWITCH_DB):
        return None
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _get_ro_db():
    if not os.path.exists(CCSWITCH_DB):
        return None
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _find_current_claude_provider(conn) -> dict | None:
    row = conn.execute(
        "SELECT id, name FROM providers WHERE app_type='claude' AND is_current=1 AND name != ?",
        (PROXY_PROVIDER_NAME,),
    ).fetchone()
    if row:
        return {"id": row["id"], "name": row["name"]}
    return None


@router.get("/status")
def setup_status():
    """Check if proxy setup is done."""
    conn = _get_ro_db()
    if not conn:
        return {"ccswitch_available": False, "proxy_configured": False}

    try:
        exists = conn.execute(
            "SELECT id FROM providers WHERE name = ?", (PROXY_PROVIDER_NAME,)
        ).fetchone()

        current = None
        settings = {}
        if os.path.exists(CCSWITCH_SETTINGS):
            with open(CCSWITCH_SETTINGS, "r") as f:
                settings = json.load(f)
            cid = settings.get("currentProviderClaude", "")
            if cid:
                row = conn.execute(
                    "SELECT name FROM providers WHERE id = ?", (cid,)
                ).fetchone()
                if row:
                    current = row["name"]

        return {
            "ccswitch_available": True,
            "proxy_configured": exists is not None,
            "current_provider": current,
            "proxy_base_url": "http://localhost:15722",
        }
    finally:
        conn.close()


@router.post("/apply")
def apply_setup():
    """One-click setup: create RAgent Proxy provider and set it as active.

    Saves the previous provider ID so it can be reverted later.
    """
    conn = _get_rw_db()
    if not conn:
        raise HTTPException(500, "CC Switch database not found")
    if not os.path.exists(CCSWITCH_SETTINGS):
        raise HTTPException(500, "CC Switch settings not found")

    try:
        # Check if already set up
        existing = conn.execute(
            "SELECT id FROM providers WHERE name = ?", (PROXY_PROVIDER_NAME,)
        ).fetchone()
        if existing:
            raise HTTPException(400, "RAgent Proxy is already configured")

        # Save current state for revert
        current = conn.execute(
            "SELECT id FROM providers WHERE app_type='claude' AND is_current=1"
        ).fetchone()
        previous_id = current["id"] if current else None

        # Find a provider to copy config from (prefer DeepSeek)
        template = conn.execute(
            "SELECT settings_config FROM providers "
            "WHERE id = '98aa7573-be9b-49b2-9a74-4e645e520f9e'"
        ).fetchone()
        if not template:
            template = conn.execute(
                "SELECT settings_config FROM providers "
                "WHERE app_type='claude' AND settings_config IS NOT NULL "
                "AND name != 'default' LIMIT 1"
            ).fetchone()
        if not template or not template["settings_config"]:
            raise HTTPException(500, "No template provider with API config found")

        cfg = json.loads(template["settings_config"])
        env = cfg.get("env", {})
        env["ANTHROPIC_BASE_URL"] = "http://localhost:15722"
        cfg["env"] = env

        new_id = str(uuid.uuid4())

        conn.execute(
            """INSERT INTO providers
               (id, app_type, name, category, settings_config, is_current,
                in_failover_queue, cost_multiplier, icon_color, created_at)
               VALUES (?, 'claude', ?, 'custom', ?, 1, 0, '1.0', '#6366f1', 0)""",
            (new_id, PROXY_PROVIDER_NAME, json.dumps(cfg)),
        )
        conn.execute(
            "UPDATE providers SET is_current = 0 WHERE app_type = 'claude' AND id != ?",
            (new_id,),
        )
        # Also insert the endpoint URL — CC Switch reads this to route requests
        conn.execute(
            "INSERT INTO provider_endpoints (provider_id, app_type, url, added_at) "
            "VALUES (?, 'claude', ?, 0)",
            (new_id, "http://localhost:15722"),
        )
        conn.commit()

        # Update settings.json
        with open(CCSWITCH_SETTINGS, "r") as f:
            settings = json.load(f)
        settings["_ragent_previous_provider"] = previous_id
        settings["currentProviderClaude"] = new_id
        with open(CCSWITCH_SETTINGS, "w") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        # Update Claude Code settings — this is what Claude Code actually reads
        previous_claude_url = None
        if os.path.exists(CLAUDE_SETTINGS):
            with open(CLAUDE_SETTINGS, "r") as f:
                claude_cfg = json.load(f)
            env = claude_cfg.get("env", {})
            previous_claude_url = env.get("ANTHROPIC_BASE_URL", "")
            env["ANTHROPIC_BASE_URL"] = PROXY_URL
            claude_cfg["env"] = env
            claude_cfg["_ragent_previous_base_url"] = previous_claude_url
            with open(CLAUDE_SETTINGS, "w") as f:
                json.dump(claude_cfg, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "proxy_id": new_id,
            "previous_id": previous_id,
            "message": "RAgent Proxy is now active. All Claude Code requests go through RAgent Router.",
        }
    finally:
        conn.close()


@router.post("/revert")
def revert_setup():
    """Undo the proxy setup — restore previous provider and remove proxy entry."""
    conn = _get_rw_db()
    if not conn:
        raise HTTPException(500, "CC Switch database not found")

    try:
        proxy_row = conn.execute(
            "SELECT id FROM providers WHERE name = ?", (PROXY_PROVIDER_NAME,)
        ).fetchone()
        if not proxy_row:
            raise HTTPException(400, "RAgent Proxy not found — nothing to revert")

        # Restore Claude Code settings
        if os.path.exists(CLAUDE_SETTINGS):
            with open(CLAUDE_SETTINGS, "r") as f:
                claude_cfg = json.load(f)
            previous_url = claude_cfg.pop("_ragent_previous_base_url", None)
            if previous_url:
                env = claude_cfg.get("env", {})
                env["ANTHROPIC_BASE_URL"] = previous_url
                claude_cfg["env"] = env
            with open(CLAUDE_SETTINGS, "w") as f:
                json.dump(claude_cfg, f, indent=2, ensure_ascii=False)

        # Read previous provider from settings
        previous_id = None
        if os.path.exists(CCSWITCH_SETTINGS):
            with open(CCSWITCH_SETTINGS, "r") as f:
                settings = json.load(f)
            previous_id = settings.pop("_ragent_previous_provider", None)
            if previous_id:
                settings["currentProviderClaude"] = previous_id
            with open(CCSWITCH_SETTINGS, "w") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

        # Remove proxy provider and its endpoint
        conn.execute("DELETE FROM provider_endpoints WHERE provider_id = ?", (proxy_row["id"],))
        conn.execute("DELETE FROM providers WHERE id = ?", (proxy_row["id"],))

        # Restore previous provider
        if previous_id:
            conn.execute("UPDATE providers SET is_current = 0 WHERE app_type = 'claude'")
            conn.execute("UPDATE providers SET is_current = 1 WHERE id = ?", (previous_id,))
        else:
            # Fallback: re-enable DeepSeek
            conn.execute("UPDATE providers SET is_current = 0 WHERE app_type = 'claude'")
            conn.execute(
                "UPDATE providers SET is_current = 1 "
                "WHERE id = '98aa7573-be9b-49b2-9a74-4e645e520f9e'"
            )

        conn.commit()

        restored_name = "original provider"
        if previous_id:
            row = conn.execute(
                "SELECT name FROM providers WHERE id = ?", (previous_id,)
            ).fetchone()
            if row:
                restored_name = row["name"]

        return {
            "success": True,
            "restored_provider": restored_name,
            "message": f"Reverted to {restored_name}. RAgent Proxy has been removed.",
        }
    finally:
        conn.close()
