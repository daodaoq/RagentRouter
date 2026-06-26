"""Transparent proxy — Claude Code → RAgent Router → real provider API.

Flow (zero added latency):
  1. Receive /v1/messages request from Claude Code (routed via CC Switch)
  2. Forward immediately to the currently-active CC Switch provider
  3. Stream response back to Claude Code
  4. Background: classify the user's question → if a better provider is found,
     switch for the NEXT request
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["Proxy"])

log = logging.getLogger("ragent.proxy")

CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")

# ── Provider adapters ─────────────────────────────────────────────────
# Each provider has quirks. Map provider name → adapter config.
# New providers: just add an entry here.

PROVIDER_ADAPTERS = {
    "MiniMax": {
        # MiniMax requires capitalized X-Api-Key header (not x-api-key)
        "auth_header": "X-Api-Key",
        # MiniMax expects model name without [1m] suffix
        "model_rewrite": None,  # keep original model from request (MiniMax-M3)
    },
    "Bailian": {
        "auth_header": "x-api-key",
        "model_rewrite": None,
    },
    "DeepSeek": {
        "auth_header": "x-api-key",
        "model_rewrite": None,
    },
}

# Default adapter for unknown providers
_DEFAULT_ADAPTER = {
    "auth_header": "x-api-key",
    "model_rewrite": None,
}


def _get_adapter(provider_name: str) -> dict:
    """Get the adapter config for a provider, falling back to defaults."""
    for key, adapter in PROVIDER_ADAPTERS.items():
        if key.lower() in provider_name.lower():
            return adapter
    return _DEFAULT_ADAPTER


def ensure_proxy_active():
    """Startup hook: ensure RAgent Proxy is active in CC Switch + settings.json.

    Called once on backend startup. Ensures Claude Code routes through us
    even after a backend restart.
    """
    if not os.path.exists(CCSWITCH_DB):
        log.warning("PROXY | CC Switch DB not found — cannot activate proxy")
        return

    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # Check if RAgent Proxy provider exists
        row = conn.execute(
            "SELECT id, settings_config FROM providers WHERE name = 'RAgent Proxy'"
        ).fetchone()

        proxy_id = row["id"] if row else None

        if not proxy_id:
            # Create RAgent Proxy provider
            import uuid
            proxy_id = str(uuid.uuid4())
            proxy_config = json.dumps({
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "ragent-proxy-local",
                    "ANTHROPIC_BASE_URL": "http://localhost:15722",
                    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
                }
            })
            conn.execute(
                "INSERT INTO providers (id, app_type, name, category, settings_config, is_current) "
                "VALUES (?, 'claude', 'RAgent Proxy', 'custom', ?, 1)",
                (proxy_id, proxy_config),
            )
            conn.execute(
                "INSERT INTO provider_endpoints (provider_id, app_type, url) "
                "VALUES (?, 'claude', 'http://localhost:15722')",
                (proxy_id,),
            )
            log.info("PROXY | created RAgent Proxy provider (%s)", proxy_id[:12])
        else:
            # Update settings_config (may have changed)
            proxy_config = json.dumps({
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "ragent-proxy-local",
                    "ANTHROPIC_BASE_URL": "http://localhost:15722",
                    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
                }
            })
            conn.execute(
                "UPDATE providers SET settings_config = ?, is_current = 1 WHERE id = ?",
                (proxy_config, proxy_id),
            )

        # Unset is_current for other claude providers
        conn.execute(
            "UPDATE providers SET is_current = 0 "
            "WHERE app_type = 'claude' AND name != 'RAgent Proxy'"
        )

        conn.commit()
    finally:
        conn.close()

    # Write to ~/.claude/settings.json so Claude Code uses us
    claude_settings = os.path.expanduser(r"~\.claude\settings.json")
    os.makedirs(os.path.dirname(claude_settings), exist_ok=True)

    existing = {}
    if os.path.exists(claude_settings):
        with open(claude_settings, "r", encoding="utf-8") as f:
            existing = json.load(f)

    proxy_env = {
        "ANTHROPIC_AUTH_TOKEN": "ragent-proxy-local",
        "ANTHROPIC_BASE_URL": "http://localhost:15722",
        "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    }
    merged = {**existing, "env": {**existing.get("env", {}), **proxy_env}}
    with open(claude_settings, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    log.info("PROXY | activated — Claude Code routes through localhost:15722")

# ── helpers ──────────────────────────────────────────────────────────


def _read_ccswitch_db(readonly: bool = True):
    if not os.path.exists(CCSWITCH_DB):
        return None
    mode = "ro" if readonly else "rw"
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _get_current_provider_config() -> Optional[dict]:
    """Resolve which real provider the proxy should forward to.

    Priority:
      1. RAgent Proxy's `notes` field (set by classifier)
      2. The is_current=1 claude provider (excluding RAgent Proxy + localhost)
    Returns {provider_id, name, base_url, api_key, model} or None.
    """
    conn = _read_ccswitch_db()
    if not conn:
        return None
    try:
        # 1. Check RAgent Proxy's notes for a preferred provider
        notes_row = conn.execute(
            "SELECT notes FROM providers WHERE name = 'RAgent Proxy'"
        ).fetchone()
        preferred_id = notes_row["notes"] if notes_row and notes_row["notes"] else None

        # 2. Build candidate list (skip RAgent Proxy + localhost + empty keys)
        rows = conn.execute(
            "SELECT id, name, settings_config, is_current FROM providers "
            "WHERE app_type = 'claude' AND name != 'default' AND name != 'RAgent Proxy' "
            "AND settings_config IS NOT NULL "
            "ORDER BY is_current DESC"
        ).fetchall()

        # Try preferred first
        if preferred_id:
            for row in rows:
                if row["id"] != preferred_id:
                    continue
                cfg = _parse_provider_config(row)
                if cfg:
                    return cfg
            # Preferred provider was deleted; clear the notes
            _clear_proxy_preference()

        # Fall back to is_current=1 (then any)
        for row in rows:
            cfg = _parse_provider_config(row)
            if cfg:
                return cfg
        return None
    except Exception as e:
        log.warning("PROXY | failed to read provider config: %s", e)
        return None
    finally:
        conn.close()


def _parse_provider_config(row) -> Optional[dict]:
    """Extract API config from a CC Switch provider row, skipping localhost/empty."""
    if not row["settings_config"]:
        return None
    try:
        cfg = json.loads(row["settings_config"])
        env = cfg.get("env", {})
        base_url = (env.get("ANTHROPIC_BASE_URL") or "").rstrip("/")
        api_key = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or ""
        if "localhost" in base_url or "127.0.0.1" in base_url:
            return None
        if not api_key:
            return None
        return {
            "provider_id": row["id"],
            "name": row["name"],
            "base_url": base_url,
            "api_key": api_key,
            "model": env.get("ANTHROPIC_MODEL") or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or "",
        }
    except (json.JSONDecodeError, KeyError):
        return None


def _clear_proxy_preference():
    conn = _read_ccswitch_db(readonly=False)
    if not conn:
        return
    try:
        conn.execute("UPDATE providers SET notes = NULL WHERE name = 'RAgent Proxy'")
        conn.commit()
    finally:
        conn.close()


def _set_proxy_preference(provider_id: str):
    """Store the preferred real provider ID in RAgent Proxy's notes field.

    RAgent Proxy stays is_current=1 in CC Switch — Claude Code keeps routing
    through us. Only the `notes` field tracks which real provider to forward to.
    """
    conn = _read_ccswitch_db(readonly=False)
    if not conn:
        return
    try:
        conn.execute(
            "UPDATE providers SET notes = ? WHERE name = 'RAgent Proxy'",
            (provider_id,),
        )
        conn.commit()
    finally:
        conn.close()


def _get_provider_config_by_id(provider_id: str) -> Optional[dict]:
    """Read a specific provider's API config by UUID."""
    conn = _read_ccswitch_db()
    if not conn:
        return None
    try:
        row = conn.execute(
            "SELECT id, name, settings_config FROM providers WHERE id = ?",
            (provider_id,),
        ).fetchone()
        if not row or not row["settings_config"]:
            return None
        cfg = json.loads(row["settings_config"])
        env = cfg.get("env", {})
        return {
            "provider_id": row["id"],
            "name": row["name"],
            "base_url": (env.get("ANTHROPIC_BASE_URL") or "").rstrip("/"),
            "api_key": env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or "",
            "model": env.get("ANTHROPIC_MODEL") or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or "",
        }
    except Exception as e:
        log.warning("PROXY | failed to read provider %s: %s", provider_id, e)
        return None
    finally:
        conn.close()


def _extract_user_question(body_json: dict) -> str:
    """Pull the last user message from an Anthropic Messages API request body."""
    messages = body_json.get("messages") or []
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                # content may be [{type: "text", text: "..."}, ...]
                parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                return " ".join(parts)
            return str(content)
    return ""


def _parse_usage_from_chunk(chunk: bytes, state: dict):
    """Extract usage tokens and request_id from streaming SSE chunks."""
    try:
        text = chunk.decode("utf-8", errors="ignore")
    except Exception:
        return
    # Each event is "event: X\ndata: {...}\n\n"
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if not data_str or data_str == "[DONE]":
            continue
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        # message_start contains the request id
        msg = data.get("message") or {}
        if msg.get("id") and not state["upstream_request_id"]:
            state["upstream_request_id"] = msg["id"]

        # message_delta / message_start carry usage
        usage = data.get("usage") or msg.get("usage") or {}
        if usage:
            state["prompt_tokens"] = max(
                state["prompt_tokens"],
                usage.get("input_tokens", 0),
            )
            state["completion_tokens"] = max(
                state["completion_tokens"],
                usage.get("output_tokens", 0),
            )
            state["cache_read_tokens"] = max(
                state["cache_read_tokens"],
                usage.get("cache_read_input_tokens", 0),
            )
            state["cache_creation_tokens"] = max(
                state["cache_creation_tokens"],
                usage.get("cache_creation_input_tokens", 0),
            )


def _estimate_cost(provider: str, model: str,
                   prompt_tokens: int, completion_tokens: int) -> float:
    """Rough cost estimate in USD based on hardcoded rate table."""
    rates = {
        # provider_family: (input $/M, output $/M)
        ("deepseek", "deepseek"): (0.27, 1.10),
        ("minimax", "minimax"): (0.30, 1.20),
        ("bailian", "qwen"): (0.40, 1.20),
        ("claude", "claude"): (3.00, 15.00),
    }
    for (fam_kw, mod_kw), (in_rate, out_rate) in rates.items():
        if fam_kw in provider.lower() or fam_kw in model.lower():
            cost = (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000
            return round(cost, 6)
    return 0.0


def _save_request_log(state: dict, latency_ms: int):
    """Persist a single request log entry."""
    try:
        from database import SessionLocal
        from models import RequestLog
        db = SessionLocal()
        try:
            cost = _estimate_cost(
                state["provider"], state["model"],
                state["prompt_tokens"], state["completion_tokens"],
            )
            log_entry = RequestLog(
                id=state["request_id"],
                prompt=state["prompt"][:500],
                prompt_tokens=state["prompt_tokens"],
                completion_tokens=state["completion_tokens"],
                total_tokens=state["prompt_tokens"] + state["completion_tokens"],
                cache_read_tokens=state["cache_read_tokens"],
                cache_creation_tokens=state["cache_creation_tokens"],
                model=state["model"] or "unknown",
                provider=state["provider"],
                provider_id=state["provider_id"],
                upstream_url=state["upstream_url"],
                route_reason=(
                    f"matched intent={state['intent_match']} score={state['intent_score']:.2f}"
                    if state["intent_match"]
                    else f"preference={state['provider']}"
                ),
                intent_match=state["intent_match"],
                intent_score=state["intent_score"],
                status=state["status"],
                error_detail=state["error_detail"],
                upstream_request_id=state["upstream_request_id"],
                cost_usd=cost,
                latency_ms=latency_ms,
            )
            db.add(log_entry)
            db.commit()
            log.info(
                "PROXY | logged req=%s provider=%s model=%s "
                "in=%d out=%d latency=%dms cost=$%.4f",
                state["request_id"], state["provider"], state["model"],
                state["prompt_tokens"], state["completion_tokens"],
                latency_ms, cost,
            )
        finally:
            db.close()
    except Exception as e:
        log.warning("PROXY | failed to save log: %s", e)


def _resolve_proxy_preference_state() -> Optional[dict]:
    """Read intent_match/intent_score from a separate state table.

    Lightweight: just check the current RAgent Proxy notes + intent classification
    cache. Avoids a DB roundtrip on every request.
    """
    # Note: detailed intent match data is best-effort. For now return None
    # (full intent detail is in the IntentNode model — accessible via /api/intent endpoints)
    return None


async def _classify_and_switch(question: str) -> Optional[dict]:
    """Run intent classification, mark the matched provider as preferred.

    Only updates CC Switch DB is_current flag — does NOT write settings.json
    so Claude Code keeps routing through RAgent Proxy.

    Returns the classification result dict or None on failure.
    Inline import avoids circular dependency at module load time.
    """
    if not question.strip():
        return None
    try:
        from routers.intent import (
            _load_tree,
            _leaf_nodes,
            _classify_with_llm,
            _resolve_default_provider,
            INTENT_MIN_SCORE,
        )

        tree = _load_tree()
        leaves = _leaf_nodes(tree)
        if not leaves:
            log.debug("PROXY | no intent leaves, skip classification")
            return None

        scored = await _classify_with_llm(question, leaves)
        by_code = tree["by_code"]

        best_code = None
        best_score = 0.0
        best_provider_id = None
        for item in scored:
            code = item.get("id")
            score = float(item.get("score", 0))
            node = by_code.get(code)
            if node and score > best_score:
                best_score = score
                best_code = code
                best_provider_id = node.get("provider_id")

        if best_score < INTENT_MIN_SCORE or not best_provider_id:
            # No match → use default provider as preferred
            dp = _resolve_default_provider()
            if dp:
                _set_proxy_preference(dp["id"])
                log.info("PROXY | no intent match → prefer default %s", dp["name"])
            return {"matched": None, "fallback": dp["name"] if dp else None}

        # Store matched provider as preferred (in RAgent Proxy's notes, not is_current)
        try:
            _set_proxy_preference(best_provider_id)
            log.info(
                "PROXY | prefer %s (intent=%s, score=%.2f)",
                best_provider_id[:12], best_code, best_score,
            )
        except Exception as e:
            log.warning("PROXY | prefer failed: %s", e)

        return {
            "matched": best_code,
            "score": best_score,
            "provider_id": best_provider_id,
        }
    except Exception as e:
        log.warning("PROXY | classification failed: %s", e)
        return None


# ── endpoint ─────────────────────────────────────────────────────────


@router.post("/v1/messages")
@router.post("/v1/messages/")
async def proxy_messages(request: Request, background_tasks: BackgroundTasks):
    """Transparent Anthropic Messages API proxy.

    Forwards the request to the currently-active CC Switch provider,
    streams the response back, then classifies the question in background
    to switch providers for the next request.
    """
    body_bytes = await request.body()

    # Parse the request body
    try:
        body_json = json.loads(body_bytes)
    except json.JSONDecodeError:
        return StreamingResponse(
            iter([b'{"error":"Invalid JSON body"}']),
            status_code=400,
            media_type="application/json",
        )

    # Resolve the target provider to forward to
    target = _get_current_provider_config()
    if not target or not target["api_key"]:
        return StreamingResponse(
            iter([json.dumps({
                "type": "error",
                "error": {
                    "type": "proxy_error",
                    "message": "No active CC Switch provider configured. "
                               "Please activate a provider in CC Switch.",
                },
            }).encode()]),
            status_code=502,
            media_type="text/event-stream",
        )

    # Build upstream request with provider-specific adapter
    adapter = _get_adapter(target["name"])
    upstream_url = f"{target['base_url']}/v1/messages"
    upstream_headers = {
        adapter["auth_header"]: target["api_key"],
        "anthropic-version": request.headers.get("anthropic-version", "2023-06-01"),
        "content-type": "application/json",
    }

    # Sanitize model name: strip Claude Code internal suffixes like [1m],
    # then apply provider-specific rewrite if configured
    raw_model = body_json.get("model", "")
    clean_model = raw_model.split("[")[0] if raw_model else ""
    if adapter.get("model_rewrite"):
        clean_model = adapter["model_rewrite"]
    if clean_model:
        body_json["model"] = clean_model

    log.info(
        "PROXY | → %s (%s) | model=%s",
        target["name"],
        upstream_url,
        clean_model,
    )

    # Enqueue background classification (runs after response)
    question = _extract_user_question(body_json)
    if question:
        background_tasks.add_task(_classify_and_switch, question)

    # Tracking state — collected during streaming and saved when stream ends
    t_start = time.time()
    state = {
        "request_id": uuid.uuid4().hex[:12],
        "provider": target["name"],
        "provider_id": target["provider_id"],
        "model": clean_model,
        "upstream_url": upstream_url,
        "prompt": question[:500],
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "total_tokens": 0,
        "status": "ok",
        "error_detail": "",
        "upstream_request_id": "",
        "intent_match": "",
        "intent_score": 0.0,
    }

    # Pre-compute intent match (sync, no LLM) — set based on current preference
    pref_state = _resolve_proxy_preference_state()
    if pref_state:
        state["intent_match"] = pref_state.get("intent_match", "")
        state["intent_score"] = pref_state.get("intent_score", 0.0)

    # Stream the upstream response
    client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))

    async def _stream():
        try:
            async with client.stream(
                "POST",
                upstream_url,
                headers=upstream_headers,
                json=body_json,
            ) as upstream_resp:
                if upstream_resp.status_code >= 400:
                    error_body = await upstream_resp.aread()
                    state["status"] = "error"
                    state["error_detail"] = f"HTTP {upstream_resp.status_code}: {error_body.decode()[:300]}"
                    log.warning(
                        "PROXY | upstream error %s from %s: %s",
                        upstream_resp.status_code,
                        target["name"],
                        error_body[:300],
                    )
                    err_event = f"event: error\ndata: {json.dumps({'error': {'type': 'upstream_error', 'message': f'Upstream {upstream_resp.status_code}', 'body': error_body.decode()[:500]}})}\n\n".encode()
                    yield err_event
                    _save_request_log(state, int((time.time() - t_start) * 1000))
                    return

                async for chunk in upstream_resp.aiter_bytes():
                    _parse_usage_from_chunk(chunk, state)
                    yield chunk

                # Log success
                _save_request_log(state, int((time.time() - t_start) * 1000))
        except httpx.ConnectError as e:
            log.error("PROXY | connect failed for %s: %s", upstream_url, e)
            err = json.dumps({
                "type": "error",
                "error": {
                    "type": "proxy_error",
                    "message": f"Cannot reach upstream API: {target['name']}",
                },
            })
            yield f"event: error\ndata: {err}\n\n".encode()
        except Exception as e:
            log.error("PROXY | stream error: %s", e)
            err = json.dumps({
                "type": "error",
                "error": {
                    "type": "proxy_error",
                    "message": str(e)[:200],
                },
            })
            yield f"event: error\ndata: {err}\n\n".encode()
        finally:
            await client.aclose()

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "x-ragent-proxy": target["name"],
            "x-ragent-proxy-url": upstream_url,
            "cache-control": "no-cache",
            "connection": "keep-alive",
        },
    )


@router.get("/v1/messages")
async def proxy_messages_options():
    """Health check / OPTIONS for the proxy endpoint."""
    return {
        "proxy": "ragent-router",
        "endpoint": "/v1/messages",
        "method": "POST (streaming SSE)",
        "status": "ok",
    }
