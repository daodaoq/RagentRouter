from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Anthropic-compatible Messages API ──────────────────────────────

class ContentBlock(BaseModel):
    type: Literal["text", "tool_use", "tool_result", "image"]
    text: str | None = None


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str | list[ContentBlock]


class MessagesRequest(BaseModel):
    """Anthropic Messages API compatible request body."""

    model: str = "auto"
    messages: list[Message]
    max_tokens: int = 4096
    system: str | list[dict] | None = None
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    metadata: dict | None = None
    stop_sequences: list[str] | None = None


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None


class MessagesResponse(BaseModel):
    """Anthropic Messages API compatible response."""

    id: str
    type: str = "message"
    role: str = "assistant"
    content: list[ContentBlock]
    model: str
    stop_reason: str | None = "end_turn"
    stop_sequence: str | None = None
    usage: Usage


# ── Dashboard ──────────────────────────────────────────────────────

class CostOverviewOut(BaseModel):
    today_cost: float = 0.0
    month_cost: float = 0.0
    saved_amount: float = 0.0
    saving_rate: float = 0.0
    total_requests: int = 0


class ModelDistributionItem(BaseModel):
    model: str
    count: int
    percentage: float


class ModelDistributionOut(BaseModel):
    items: list[ModelDistributionItem]


class RecentRouteItem(BaseModel):
    id: str
    prompt: str
    model: str
    provider: str
    route_reason: str
    cost_usd: float
    latency_ms: int
    created_at: datetime


class RecentRoutesOut(BaseModel):
    items: list[RecentRouteItem]


class CostTrendPoint(BaseModel):
    date: str
    cost: float
    requests: int


class CostTrendOut(BaseModel):
    points: list[CostTrendPoint]


# ── Rules ──────────────────────────────────────────────────────────

class RuleIn(BaseModel):
    name: str
    description: str = ""
    keywords: list[str] = []
    target_model: str = "deepseek"
    priority: int = 0
    enabled: bool = True


class RuleOut(BaseModel):
    id: str
    name: str
    description: str
    keywords: list[str]
    target_model: str
    priority: int
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RuleUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    target_model: str | None = None
    priority: int | None = None
    enabled: bool | None = None
