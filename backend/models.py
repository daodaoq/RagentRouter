import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Session

from database import Base


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class RouteRule(Base):
    __tablename__ = "route_rules"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, comment="Rule name")
    description = Column(String, default="")
    keywords = Column(JSON, default=list, comment="Keyword list for matching")
    target_model = Column(String, nullable=False, comment="Target model (claude / deepseek)")
    priority = Column(Integer, default=0, comment="Higher priority checked first")
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(String, primary_key=True, default=gen_id)
    prompt = Column(Text, default="")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    model = Column(String, nullable=False, comment="Model actually used")
    provider = Column(String, nullable=False, comment="claude / deepseek")
    route_reason = Column(String, default="", comment="Why this model was chosen")
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def seed_demo_data(db: Session):
    """Insert demo routing rules and sample request logs."""
    # Skip if data already exists
    if db.query(RouteRule).count() > 0:
        return

    rules = [
        RouteRule(
            id="r1",
            name="Architecture & Design",
            description="Complex architecture and design tasks → Claude",
            keywords=["architecture", "design", "refactor", "system design", "架构", "设计", "重构"],
            target_model="claude",
            priority=100,
        ),
        RouteRule(
            id="r2",
            name="Bug Fix",
            description="Bug fixing and debugging → Claude",
            keywords=["bug", "fix", "debug", "error", "crash", "修复", "调试", "错误"],
            target_model="claude",
            priority=90,
        ),
        RouteRule(
            id="r3",
            name="Code Generation",
            description="Generate new code → Claude",
            keywords=["generate", "create", "write code", "implement", "生成", "创建", "实现"],
            target_model="claude",
            priority=80,
        ),
        RouteRule(
            id="r4",
            name="Simple Questions",
            description="Simple explanations and Q&A → DeepSeek",
            keywords=["explain", "what is", "how to", "why", "简单", "解释", "什么是"],
            target_model="deepseek",
            priority=70,
        ),
        RouteRule(
            id="r5",
            name="Documentation",
            description="Documentation tasks → DeepSeek",
            keywords=["document", "readme", "comment", "doc", "文档", "注释"],
            target_model="deepseek",
            priority=60,
        ),
    ]
    db.add_all(rules)

    # Sample request logs for the dashboard demo
    sample_logs = [
        RequestLog(
            id="log1",
            prompt="Design a distributed task scheduling system with Spring Boot",
            prompt_tokens=120,
            completion_tokens=850,
            total_tokens=970,
            model="claude-sonnet-4-6",
            provider="claude",
            route_reason="Matched rule: Architecture & Design (keyword: design)",
            cost_usd=0.0131,
            latency_ms=3200,
        ),
        RequestLog(
            id="log2",
            prompt="Explain how Redis transactions work",
            prompt_tokens=40,
            completion_tokens=320,
            total_tokens=360,
            model="deepseek-chat",
            provider="deepseek",
            route_reason="Matched rule: Simple Questions (keyword: explain)",
            cost_usd=0.0004,
            latency_ms=800,
        ),
        RequestLog(
            id="log3",
            prompt="Review this PR for potential bugs",
            prompt_tokens=200,
            completion_tokens=500,
            total_tokens=700,
            model="claude-sonnet-4-6",
            provider="claude",
            route_reason="Matched rule: Bug Fix (keyword: bug)",
            cost_usd=0.0091,
            latency_ms=2500,
        ),
        RequestLog(
            id="log4",
            prompt="What is Kubernetes and why should I use it?",
            prompt_tokens=30,
            completion_tokens=280,
            total_tokens=310,
            model="deepseek-chat",
            provider="deepseek",
            route_reason="Matched rule: Simple Questions (keyword: what is)",
            cost_usd=0.0003,
            latency_ms=700,
        ),
        RequestLog(
            id="log5",
            prompt="Generate a REST API controller for user CRUD operations",
            prompt_tokens=80,
            completion_tokens=600,
            total_tokens=680,
            model="claude-sonnet-4-6",
            provider="claude",
            route_reason="Matched rule: Code Generation (keyword: generate)",
            cost_usd=0.0092,
            latency_ms=2800,
        ),
        RequestLog(
            id="log6",
            prompt="Refactor this monolithic service into microservices",
            prompt_tokens=150,
            completion_tokens=920,
            total_tokens=1070,
            model="claude-sonnet-4-6",
            provider="claude",
            route_reason="Matched rule: Architecture & Design (keyword: refactor)",
            cost_usd=0.0142,
            latency_ms=3500,
        ),
        RequestLog(
            id="log7",
            prompt="Write documentation for the payment module API",
            prompt_tokens=60,
            completion_tokens=400,
            total_tokens=460,
            model="deepseek-chat",
            provider="deepseek",
            route_reason="Matched rule: Documentation (keyword: document)",
            cost_usd=0.0005,
            latency_ms=900,
        ),
        RequestLog(
            id="log8",
            prompt="How to optimize PostgreSQL query performance?",
            prompt_tokens=35,
            completion_tokens=350,
            total_tokens=385,
            model="deepseek-chat",
            provider="deepseek",
            route_reason="Matched rule: Simple Questions (keyword: how to)",
            cost_usd=0.0004,
            latency_ms=750,
        ),
    ]
    db.add_all(sample_logs)
    db.commit()
