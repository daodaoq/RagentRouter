"""CC Switch integration — display and switch providers.

Switching (matching CC Switch's own behavior):
1. Read provider's full settings_config from CC Switch DB
2. Sanitize (strip internal-only fields: api_format, openrouter_compat_mode)
3. Write directly to ~/.claude/settings.json
4. Update CC Switch DB is_current + local settings.json
"""

import json
import logging
import os
import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/ccswitch", tags=["CC Switch"])

log = logging.getLogger("ragent")

# Paths
CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")
CCSWITCH_SETTINGS = os.path.expanduser(r"~\.cc-switch\settings.json")
CLAUDE_SETTINGS = os.path.expanduser(r"~\.claude\settings.json")

# Internal fields to strip before writing to Claude Code config
SANITIZE_KEYS = {"api_format", "apiFormat", "openrouter_compat_mode", "openrouterCompatMode"}


def _get_ccswitch_db(readonly=True):
    if not os.path.exists(CCSWITCH_DB):
        return None
    mode = "ro" if readonly else "rw"
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _sanitize_settings(settings: dict) -> dict:
    """Remove CC Switch internal fields before writing to Claude Code config."""
    for key in SANITIZE_KEYS:
        settings.pop(key, None)
    return settings


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
        "db_size_mb": round(os.path.getsize(CCSWITCH_DB) / (1024 * 1024), 2) if exists else 0,
    }


# ── Activate ──────────────────────────────────────────────────────


@router.post("/activate/{provider_id}")
def activate_provider(provider_id: str):
    """Switch Claude Code's active API provider.

    Matches CC Switch's own behavior exactly:
    1. Read provider's complete settings_config
    2. Sanitize (strip internal fields)
    3. Write directly to ~/.claude/settings.json
    4. Update CC Switch DB + local settings
    """
    if not os.path.exists(CCSWITCH_DB):
        raise HTTPException(404, "CC Switch database not found")

    # 1. Read provider with full settings_config
    ro_conn = _get_ccswitch_db(readonly=True)
    try:
        provider = ro_conn.execute(
            "SELECT id, name, app_type, settings_config FROM providers "
            "WHERE id = ? AND name != 'default'",
            (provider_id,),
        ).fetchone()
        if not provider:
            raise HTTPException(404, f"Provider '{provider_id}' not found")
        if not provider["settings_config"]:
            raise HTTPException(400, f"Provider '{provider['name']}' has no configuration")

        provider_config = json.loads(provider["settings_config"])
    finally:
        ro_conn.close()

    # 2. Merge with current settings to preserve non-provider fields
    #    (permissions, theme, enabledPlugins, etc.)
    if os.path.exists(CLAUDE_SETTINGS):
        with open(CLAUDE_SETTINGS, "r", encoding="utf-8") as f:
            current_settings = json.load(f)
    else:
        current_settings = {}

    # Provider config takes priority, current settings fill in gaps
    merged = {**current_settings, **provider_config}
    # Deep-merge env separately to avoid losing provider's env keys
    if "env" in provider_config and "env" in current_settings:
        merged["env"] = {**current_settings["env"], **provider_config["env"]}

    sanitized = _sanitize_settings(merged)

    # Ensure directory exists
    claude_dir = os.path.dirname(CLAUDE_SETTINGS)
    os.makedirs(claude_dir, exist_ok=True)

    with open(CLAUDE_SETTINGS, "w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=2, ensure_ascii=False)
    log.info("SWITCH | wrote %s config to %s", provider["name"], CLAUDE_SETTINGS)

    # 3. Update CC Switch DB — is_current
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

    # 4. Update CC Switch's local settings.json
    if os.path.exists(CCSWITCH_SETTINGS):
        with open(CCSWITCH_SETTINGS, "r", encoding="utf-8") as f:
            ccs_settings = json.load(f)
    else:
        ccs_settings = {}
    ccs_settings["currentProviderClaude"] = provider_id
    with open(CCSWITCH_SETTINGS, "w", encoding="utf-8") as f:
        json.dump(ccs_settings, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "provider_id": provider_id,
        "provider_name": provider["name"],
        "message": (
            f"已切换到 '{provider['name']}' — Claude Code 下个请求自动使用新供应商，无需重启。"
        ),
    }
