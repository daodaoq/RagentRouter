"""Intent tree — CRUD + AI classification + auto-routing.

Design (mirrors the Java project's intent tree):

  Domain ── Category ── Topic (leaf, bound to a CC Switch provider)

A user asks a question → DeepSeek classifies it against every enabled leaf →
the leaf with the highest score determines the provider → that provider is
activated in `~/.claude/settings.json` (next Claude Code request uses it).

The tree is cached in-process; any write clears the cache.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from threading import Lock
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import SessionLocal
from models import IntentNode

router = APIRouter(prefix="/api/intent", tags=["Intent Tree"])
log = logging.getLogger("ragent")

# ── Constants ─────────────────────────────────────────────────────

CCSWITCH_DB = os.path.expanduser(r"~\.cc-switch\cc-switch.db")
INTENT_MIN_SCORE = 0.4  # below this we treat as "no match"
MAX_INTENT_COUNT = 5
DEFAULT_PROVIDER_KEYWORD = "deepseek"  # fallback provider name keyword

# Classifier LLM config — three-tier resolution:
#   1. Explicit env vars (DEEPSEEK_API_KEY etc.) — full override
#   2. CC Switch DB: pick any enabled provider with a configured key
#   3. Return 503 with instructions to configure
#
# This means: the user's intent classifier piggy-backs on whichever CC Switch
# provider they've already configured. No double key management.

DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "")
_classifier_cache: Optional[dict] = None


def _resolve_classifier_config() -> Optional[dict]:
    """Return {base_url, api_key, model, source, provider_name} or None."""
    global _classifier_cache

    # 1. Explicit env override
    if DEEPSEEK_KEY and DEEPSEEK_BASE:
        return {
            "base_url": DEEPSEEK_BASE,
            "api_key": DEEPSEEK_KEY,
            "model": DEEPSEEK_MODEL or "deepseek-chat",
            "source": "env",
            "provider_name": "env override",
        }

    # 2. Scan CC Switch DB
    if not os.path.exists(CCSWITCH_DB):
        return None

    try:
        conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, settings_config FROM providers "
            "WHERE name != 'default' AND settings_config IS NOT NULL"
        ).fetchall()
        conn.close()
    except Exception as e:
        log.warning("CCSWITCH scan failed: %s", e)
        return None

    # Priority: cheapest → use a known hardcoded rate table for popular providers.
    # (CC Switch itself doesn't store real API prices, so we use cost_multiplier
    # as a proxy and fall back to name-based heuristics.)
    RATES = {
        "deepseek": 0.27,    # $0.27/M input
        "bailian": 0.30,
        "minimax": 0.30,
        "minimax": 0.30,
        "moonshot": 0.50,
        "zhipu":   0.50,
        "qwen":    0.40,
        "claude":  3.00,
        "openai":  2.50,
    }

    candidates = []
    for r in rows:
        try:
            cfg = json.loads(r["settings_config"] or "{}")
            env = cfg.get("env", {})
            key = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")
            url = env.get("ANTHROPIC_BASE_URL", "")
            model = env.get("ANTHROPIC_MODEL") or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or ""
            # Skip providers with no key, no URL, or pointing to localhost
            if not key or not url:
                continue
            if "localhost" in url.lower() or "127.0.0.1" in url:
                continue
            if key == "ragent-proxy-local":
                continue
            # Try to identify the provider family by name (case-insensitive)
            family = next((k for k in RATES if k in r["name"].lower()), "other")
            rate = RATES[family]
            candidates.append({
                "base_url": url,
                "api_key": key,
                "model": model or "default",
                "source": f"ccswitch:{r['name']}",
                "provider_name": r["name"],
                "rate": rate,
            })
        except (json.JSONDecodeError, KeyError):
            continue

    if not candidates:
        return None

    # Pick the cheapest
    candidates.sort(key=lambda c: c["rate"])
    chosen = candidates[0]
    log.info("CLASSIFIER | auto-picked %s (rate=%.2f) from %d candidates",
             chosen["provider_name"], chosen["rate"], len(candidates))
    return {k: v for k, v in chosen.items() if k != "rate"}


def _get_classifier_config() -> Optional[dict]:
    """Cached resolver — config doesn't change at runtime."""
    global _classifier_cache
    if _classifier_cache is None:
        _classifier_cache = _resolve_classifier_config()
    return _classifier_cache

# ── In-process tree cache ────────────────────────────────────────

_tree_cache: Optional[dict] = None
_tree_lock = Lock()


def _invalidate_cache():
    global _tree_cache
    with _tree_lock:
        _tree_cache = None


def _load_tree() -> dict:
    """Load enabled nodes from DB, build nested tree, cache it."""
    global _tree_cache
    with _tree_lock:
        if _tree_cache is not None:
            return _tree_cache

        db = SessionLocal()
        try:
            rows = (
                db.query(IntentNode)
                .filter(IntentNode.deleted == 0, IntentNode.enabled == 1)
                .order_by(IntentNode.sort_order, IntentNode.intent_code)
                .all()
            )
        finally:
            db.close()

        by_code = {r.intent_code: _node_to_dict(r, children=[]) for r in rows}
        roots = []
        for code, node in by_code.items():
            parent = node.get("parent_code")
            if parent and parent in by_code:
                by_code[parent]["children"].append(node)
            else:
                roots.append(node)

        _tree_cache = {"roots": roots, "by_code": by_code, "loaded_at": time.time()}
        log.info("INTENT | tree loaded: %d nodes, %d roots", len(by_code), len(roots))
        return _tree_cache


def _node_to_dict(node: IntentNode, children: list) -> dict:
    return {
        "id": node.id,
        "intent_code": node.intent_code,
        "parent_code": node.parent_code,
        "name": node.name,
        "description": node.description or "",
        "level": node.level,
        "examples": node.examples or [],
        "provider_id": node.provider_id,
        "sort_order": node.sort_order,
        "enabled": bool(node.enabled),
        "children": children,
    }


# ── Pydantic schemas ─────────────────────────────────────────────


class NodeIn(BaseModel):
    intent_code: str = Field(..., min_length=1, max_length=64)
    parent_code: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    level: int = Field(2, ge=0, le=2)  # 0=DOMAIN, 1=CATEGORY, 2=TOPIC
    examples: list[str] = []
    provider_id: Optional[str] = None
    sort_order: int = 0
    enabled: bool = True


class NodePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_code: Optional[str] = None
    examples: Optional[list[str]] = None
    provider_id: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None
    level: Optional[int] = Field(None, ge=0, le=2)


class ClassifyRequest(BaseModel):
    question: str = Field(..., min_length=1)
    auto_switch: bool = False  # if True, activate the matched provider


# ── CRUD endpoints ───────────────────────────────────────────────


@router.get("/tree")
def get_tree():
    """Return the full nested intent tree (enabled nodes only)."""
    return _load_tree()


@router.get("/classifier")
def classifier_status():
    """Which LLM is being used for intent classification right now."""
    cfg = _get_classifier_config()
    if not cfg:
        return {
            "configured": False,
            "message": (
                "Set DEEPSEEK_API_KEY env var, or add a Claude/Anthropic provider "
                "in CC Switch with a valid API key."
            ),
        }
    return {
        "configured": True,
        "provider_name": cfg["provider_name"],
        "model": cfg["model"],
        "source": cfg["source"],
    }


_default_provider_cache: Optional[dict] = None


def _resolve_default_provider() -> Optional[dict]:
    """Find the fallback provider (DeepSeek by default) from CC Switch DB.

    Returns {id, name} or None. Cached — called once per process lifetime.
    """
    global _default_provider_cache
    if _default_provider_cache is not None:
        return _default_provider_cache

    if not os.path.exists(CCSWITCH_DB):
        _default_provider_cache = {}
        return None

    try:
        conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name FROM providers "
            "WHERE name != 'default' AND app_type = 'claude' "
            "ORDER BY is_current DESC"
        ).fetchall()
        conn.close()
    except Exception as e:
        log.warning("DEFAULT PROVIDER | DB read failed: %s", e)
        _default_provider_cache = {}
        return None

    # Prefer name containing DEFAULT_PROVIDER_KEYWORD, then current, then first
    for r in rows:
        if DEFAULT_PROVIDER_KEYWORD in r["name"].lower():
            result = {"id": r["id"], "name": r["name"]}
            _default_provider_cache = result
            log.info("DEFAULT PROVIDER | %s (%s)", r["name"], r["id"][:12])
            return result

    # Fallback: pick the currently-active claude provider
    for r in rows:
        result = {"id": r["id"], "name": r["name"]}
        _default_provider_cache = result
        log.info("DEFAULT PROVIDER | fallback → %s (%s)", r["name"], r["id"][:12])
        return result

    _default_provider_cache = {}
    return None


@router.get("/default-provider")
def get_default_provider():
    """Which provider serves as the fallback when intent doesn't match."""
    dp = _resolve_default_provider()
    if dp:
        return {"found": True, **dp}
    return {"found": False, "message": "No Claude-compatible provider in CC Switch"}


@router.get("/nodes")
def list_nodes(include_disabled: bool = False):
    db = SessionLocal()
    try:
        q = db.query(IntentNode).filter(IntentNode.deleted == 0)
        if not include_disabled:
            q = q.filter(IntentNode.enabled == 1)
        nodes = q.order_by(IntentNode.level, IntentNode.sort_order).all()
        return {"items": [_node_to_dict(n, children=[]) for n in nodes]}
    finally:
        db.close()


@router.post("/nodes")
def create_node(payload: NodeIn):
    db = SessionLocal()
    try:
        existing = (
            db.query(IntentNode)
            .filter(IntentNode.intent_code == payload.intent_code,
                    IntentNode.deleted == 0)
            .first()
        )
        if existing:
            raise HTTPException(409, f"intent_code '{payload.intent_code}' already exists")

        node = IntentNode(
            intent_code=payload.intent_code,
            parent_code=payload.parent_code,
            name=payload.name,
            description=payload.description,
            level=payload.level,
            examples=payload.examples,
            provider_id=payload.provider_id,
            sort_order=payload.sort_order,
            enabled=1 if payload.enabled else 0,
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        _invalidate_cache()
        return {"id": node.id, "intent_code": node.intent_code}
    finally:
        db.close()


@router.patch("/nodes/{intent_code}")
def update_node(intent_code: str, payload: NodePatch):
    db = SessionLocal()
    try:
        node = (
            db.query(IntentNode)
            .filter(IntentNode.intent_code == intent_code,
                    IntentNode.deleted == 0)
            .first()
        )
        if not node:
            raise HTTPException(404, f"Node '{intent_code}' not found")

        data = payload.model_dump(exclude_unset=True)
        if "enabled" in data:
            data["enabled"] = 1 if data["enabled"] else 0
        for k, v in data.items():
            setattr(node, k, v)
        db.commit()
        _invalidate_cache()
        return {"success": True, "intent_code": intent_code}
    finally:
        db.close()


@router.delete("/nodes/{intent_code}")
def delete_node(intent_code: str):
    """Soft delete + cascade to descendants."""
    db = SessionLocal()
    try:
        target = (
            db.query(IntentNode)
            .filter(IntentNode.intent_code == intent_code,
                    IntentNode.deleted == 0)
            .first()
        )
        if not target:
            raise HTTPException(404, f"Node '{intent_code}' not found")

        # Collect descendants by walking children
        to_delete = [target.intent_code]
        frontier = [target.intent_code]
        while frontier:
            kids = (
                db.query(IntentNode.intent_code)
                .filter(IntentNode.parent_code.in_(frontier),
                        IntentNode.deleted == 0)
                .all()
            )
            frontier = [k[0] for k in kids]
            to_delete.extend(frontier)

        db.query(IntentNode).filter(IntentNode.intent_code.in_(to_delete)).update(
            {"deleted": 1}, synchronize_session=False
        )
        db.commit()
        _invalidate_cache()
        return {"deleted": to_delete}
    finally:
        db.close()


# ── Classification ───────────────────────────────────────────────


def _leaf_nodes(tree: dict) -> list[dict]:
    """Flatten the tree, returning only enabled leaves (level=TOPIC)."""
    out = []

    def walk(node):
        if not node.get("enabled"):
            return
        kids = node.get("children") or []
        if not kids and node.get("level") == 2:
            out.append(node)
        for c in kids:
            walk(c)

    for root in tree["roots"]:
        walk(root)
    return out


def _build_classifier_prompt(question: str, leaves: list[dict]) -> str:
    leaf_lines = []
    for n in leaves:
        examples = " / ".join((n.get("examples") or [])[:5])
        leaf_lines.append(
            f"- id={n['intent_code']}\n"
            f"  path={n.get('name')}\n"
            f"  description={n.get('description', '')}\n"
            f"  examples={examples}"
        )
    catalog = "\n".join(leaf_lines)

    return f"""You are an intent classifier. Given the user's question and a catalog of intent leaves, output a JSON array of objects scored 0.0–1.0 for how well each leaf matches the question. Higher score = better match. Output ONLY the JSON array, nothing else.

Question: {question}

Intent catalog:
{catalog}

Output format (strict JSON array):
[{{"id": "<intent_code>", "score": 0.0, "reason": "<short why>"}}]
"""


async def _classify_with_llm(question: str, leaves: list[dict]) -> list[dict]:
    """Call the configured LLM (env or cheapest CC Switch provider) to score leaves."""
    if not leaves:
        return []

    cfg = _get_classifier_config()
    if not cfg:
        raise HTTPException(
            503,
            "No classifier LLM configured. Either set DEEPSEEK_API_KEY + "
            "DEEPSEEK_BASE_URL env vars, or add a provider in CC Switch."
        )

    prompt = _build_classifier_prompt(question, leaves)

    payload = {
        "model": cfg["model"],
        "max_tokens": 1024,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    # DeepSeek uses OpenAI-style /v1/chat/completions. Anthropic-style providers
    # (Claude, Bailian anthropic endpoint) use /v1/messages with a different body.
    # We pick the format based on URL hints.
    base = cfg["base_url"].rstrip("/")
    if "/anthropic" in base or base.endswith("/anthropic"):
        # Anthropic Messages API
        payload = {
            "model": cfg["model"],
            "max_tokens": 1024,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}],
        }
        anthropic_headers = {
            "x-api-key": cfg["api_key"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{base}/v1/messages",
                json=payload, headers=anthropic_headers,
            )
            if r.status_code != 200:
                log.error("CLASSIFY | LLM %s: %s", r.status_code, r.text[:300])
                raise HTTPException(502, f"Classifier LLM error {r.status_code}")
            data = r.json()
        raw = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw += block.get("text", "")
    else:
        # OpenAI-compatible
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{base}/v1/chat/completions",
                json=payload, headers=headers,
            )
            if r.status_code != 200:
                log.error("CLASSIFY | LLM %s: %s", r.status_code, r.text[:300])
                raise HTTPException(502, f"Classifier LLM error {r.status_code}")
            data = r.json()
        raw = data["choices"][0]["message"]["content"].strip()

    # Strip ```json fences if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        scored = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("CLASSIFY | bad JSON: %s | raw=%s", e, raw[:300])
        raise HTTPException(502, f"Classifier returned invalid JSON")

    # Tolerate {"results": [...]} wrapping
    if isinstance(scored, dict) and "results" in scored:
        scored = scored["results"]

    return scored if isinstance(scored, list) else []


def _ccswitch_provider_name(provider_id: Optional[str]) -> Optional[str]:
    """Resolve provider_id → display name from CC Switch DB."""
    if not provider_id or not os.path.exists(CCSWITCH_DB):
        return None
    try:
        conn = sqlite3.connect(f"file:{CCSWITCH_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT name FROM providers WHERE id = ?", (provider_id,)
        ).fetchone()
        conn.close()
        return row["name"] if row else None
    except Exception as e:
        log.warning("CCSWITCH lookup failed: %s", e)
        return None


@router.post("/classify")
async def classify(req: ClassifyRequest):
    """Classify a question against all enabled leaves, optionally auto-switch."""
    tree = _load_tree()
    leaves = _leaf_nodes(tree)
    if not leaves:
        raise HTTPException(400, "No enabled intent leaves in tree")

    scored = await _classify_with_llm(req.question, leaves)
    by_code = tree["by_code"]

    enriched = []
    for item in scored:
        code = item.get("id")
        score = float(item.get("score", 0))
        node = by_code.get(code)
        if not node:
            continue
        enriched.append({
            "intent_code": code,
            "name": node.get("name"),
            "description": node.get("description"),
            "score": score,
            "reason": item.get("reason", ""),
            "provider_id": node.get("provider_id"),
            "provider_name": _ccswitch_provider_name(node.get("provider_id")),
        })

    enriched.sort(key=lambda x: x["score"], reverse=True)
    top = [x for x in enriched if x["score"] >= INTENT_MIN_SCORE][:MAX_INTENT_COUNT]

    default_p = _resolve_default_provider()

    result = {
        "question": req.question,
        "candidates": enriched,
        "top": top,
        "matched": top[0] if top else None,
        "default_provider": default_p,
    }

    # ── Auto-switch logic ───────────────────────────────────────
    if req.auto_switch:
        from routers.ccswitch import activate_provider

        matched = result["matched"]
        # 1. Matched leaf has a bound provider → use it
        if matched and matched.get("provider_id"):
            try:
                result["switched"] = activate_provider(matched["provider_id"])
            except HTTPException as e:
                result["switched"] = {"success": False, "detail": e.detail}
        # 2. No match / no provider bound → fall back to default (DeepSeek)
        elif default_p:
            try:
                fallback_result = activate_provider(default_p["id"])
                fallback_result["fallback"] = True
                fallback_result["reason"] = (
                    "No intent matched" if not matched
                    else "Matched intent has no provider bound"
                )
                result["switched"] = fallback_result
            except HTTPException as e:
                result["switched"] = {"success": False, "detail": e.detail,
                                      "fallback": True}
        else:
            result["switched"] = {
                "success": False, "fallback": False,
                "detail": "No match and no default provider configured",
            }

    return result