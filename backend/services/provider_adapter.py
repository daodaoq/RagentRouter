"""Transparent proxy — forward requests to the active provider's Anthropic endpoint.

Reads API credentials from CC Switch DB, forwards requests unchanged,
streams responses back. Falls back to mock if CC Switch is unavailable.
"""

import asyncio
import json
import os
import sqlite3
from typing import AsyncIterator

import httpx

from config import settings

CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")

# ── Cost rates ─────────────────────────────────────────────────────

COST_RATES = {
    "claude": {"input": 3.0, "output": 15.0},
    "deepseek": {"input": 0.27, "output": 1.10},
}

MOCK_RESPONSES = {
    "default": "RAgent Router proxy is active. "
    "This is a fallback response — real forwarding requires CC Switch with configured providers.",
}


def _get_provider_config(provider_id: str) -> dict | None:
    """Read API key + base URL from CC Switch."""
    if not os.path.exists(CCSWITCH_DB):
        return None
    conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, name, settings_config FROM providers WHERE id = ?",
            (provider_id,),
        ).fetchone()
        if not row or not row["settings_config"]:
            return None

        cfg = json.loads(row["settings_config"])
        env = cfg.get("env", {})

        base_url = env.get("ANTHROPIC_BASE_URL", "")
        # Clean up URL: remove trailing path if present, add /v1/messages later
        if "/anthropic" in base_url:
            base_url = base_url.split("/anthropic")[0]
        base_url = base_url.rstrip("/")

        return {
            "provider_id": row["id"],
            "provider_name": row["name"],
            "api_key": env.get("ANTHROPIC_AUTH_TOKEN", ""),
            "base_url": base_url,
            "model": env.get("ANTHROPIC_MODEL", "deepseek-chat"),
            "anthropic_endpoint": env.get("ANTHROPIC_BASE_URL", ""),
        }
    finally:
        conn.close()


# ── Real HTTP forwarding ────────────────────────────────────────────


async def forward_to_provider(
    provider_id: str,
    system_prompt: str | None,
    messages: list[dict],
    max_tokens: int,
    stream: bool = False,
) -> dict:
    """Forward a request to the active provider and return the response."""

    cfg = _get_provider_config(provider_id)

    if not cfg or not cfg["api_key"]:
        # Fallback to demo/mock mode
        return await _mock_response()

    # Build Anthropic-format request body (pass through unchanged)
    body = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if system_prompt:
        body["system"] = system_prompt

    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    url = f"{cfg['base_url']}/v1/messages"

    async with httpx.AsyncClient(timeout=120.0) as client:
        if stream:
            # Return as streaming generator
            return await _stream_forward(client, url, headers, body, cfg)
        else:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code != 200:
                return _error_response(resp.status_code, resp.text)

            data = resp.json()
            content = data.get("content", [])
            text = "".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )

            usage = data.get("usage", {})
            return {
                "text": text or " ",
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "model": cfg["model"],
            }


async def _stream_forward(
    client: httpx.AsyncClient, url: str, headers: dict, body: dict, cfg: dict
) -> dict:
    """Streaming forward — collect full text while generating SSE events."""
    chunks = []
    async with client.stream("POST", url, json=body, headers=headers, timeout=120.0) as resp:
        if resp.status_code != 200:
            body_text = await resp.aread()
            return _error_response(resp.status_code, body_text.decode())

        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    continue
                try:
                    data = json.loads(data_str)
                    event_type = data.get("type", "")
                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            chunks.append(text)
                    elif event_type == "message_delta":
                        # Extract usage info if present
                        pass
                except json.JSONDecodeError:
                    pass

    text = "".join(chunks) or " "
    return {
        "text": text,
        "input_tokens": _estimate_tokens(str(body.get("messages", ""))),
        "output_tokens": _estimate_tokens(text),
        "model": cfg["model"],
        "stream_chunks": chunks,
    }


def _error_response(status: int, body: str) -> dict:
    return {
        "text": f"[Proxy Error {status}] {body[:300]}",
        "input_tokens": 0,
        "output_tokens": 0,
        "model": "unknown",
        "error": True,
    }


async def _mock_response() -> dict:
    return {
        "text": MOCK_RESPONSES["default"],
        "input_tokens": 10,
        "output_tokens": 20,
        "model": "mock",
    }


# ── Streaming SSE generator (for server-sent events) ────────────────


async def stream_to_client(
    provider_id: str,
    system_prompt: str | None,
    messages: list[dict],
    max_tokens: int,
) -> AsyncIterator[str]:
    """Generator that yields SSE events in real-time from provider."""

    cfg = _get_provider_config(provider_id)

    if not cfg or not cfg["api_key"]:
        # Fallback mock stream
        msg_id = "msg_mock"
        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'model': 'mock'}})}\n\n"
        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
        yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': MOCK_RESPONSES['default']}})}\n\n"
        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
        yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': 20}})}\n\n"
        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
        return

    body = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if system_prompt:
        body["system"] = system_prompt

    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    url = f"{cfg['base_url']}/v1/messages"

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            if resp.status_code != 200:
                err_text = await resp.aread()
                yield f"event: error\ndata: {json.dumps({'error': f'Proxy error {resp.status_code}: {err_text.decode()[:200]}'})}\n\n"
                return

            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    yield f"{line}\n\n"
                elif line.strip() == "":
                    yield "\n"


# ── Helpers ─────────────────────────────────────────────────────────


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def estimate_tokens(text: str) -> int:
    return _estimate_tokens(text)
