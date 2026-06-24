from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from models import RouteRule

log = logging.getLogger("ragent.route")

if TYPE_CHECKING:
    pass


def select_model(
    db: Session,
    user_message: str,
    system_prompt: str | None = None,
) -> dict:
    """Rule-based routing engine.

    Checks each rule (ordered by priority desc) and returns the first match.
    Falls back to 'deepseek' (cheaper) for unmatched requests.
    """
    combined_text = (system_prompt or "") + " " + user_message
    combined_lower = combined_text.lower()

    # Get all enabled rules, sorted by priority (highest first)
    rules = (
        db.query(RouteRule)
        .filter(RouteRule.enabled == 1)
        .order_by(RouteRule.priority.desc())
        .all()
    )

    for rule in rules:
        keywords: list[str] = rule.keywords or []
        for kw in keywords:
            # Simple keyword matching (case-insensitive)
            if kw.lower() in combined_lower:
                log.info("MATCH  | rule=%-24s | keyword=%-12s | → %s", rule.name, kw, rule.target_model)
                return {
                    "provider": rule.target_model,
                    "model": _resolve_model_name(rule.target_model),
                    "rule_name": rule.name,
                    "reason": f"Matched rule: {rule.name} (keyword: {kw})",
                    "matched_keyword": kw,
                }

    # Fallback
    log.debug("FALLBACK | no rule matched → deepseek")
    return {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "rule_name": "Default",
        "reason": "No rule matched — defaulting to DeepSeek (cost-efficient)",
        "matched_keyword": None,
    }


def _resolve_model_name(provider: str) -> str:
    if provider == "claude":
        return "claude-sonnet-4-6"
    elif provider == "deepseek":
        return "deepseek-chat"
    return provider


def match_rule(
    db: Session,
    user_message: str,
    system_prompt: str | None = None,
) -> dict:
    """Alias for select_model."""
    return select_model(db, user_message, system_prompt)
