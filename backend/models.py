import os
import sqlite3
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Session

from database import Base


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(String, primary_key=True, default=gen_id)
    prompt = Column(Text, default="", comment="First 500 chars of user question")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    cache_creation_tokens = Column(Integer, default=0)
    model = Column(String, nullable=False, comment="Model actually used by upstream")
    provider = Column(String, nullable=False, comment="CC Switch provider name")
    provider_id = Column(String, default="", index=True, comment="CC Switch provider UUID")
    upstream_url = Column(String, default="", comment="Upstream API URL")
    route_reason = Column(String, default="", comment="Why this provider was chosen")
    intent_match = Column(String, default="", comment="Matched intent code if any")
    intent_score = Column(Float, default=0.0)
    status = Column(String, default="ok", comment="ok | error")
    error_detail = Column(Text, default="")
    upstream_request_id = Column(String, default="")
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class IntentNode(Base):
    """Intent tree node — domain → category → topic hierarchy.

    Leaf nodes (level=TOPIC) are bound to a CC Switch provider via `provider_id`.
    Classification walks the tree and picks the leaf that best matches the
    user's question, then activates the bound provider.
    """

    __tablename__ = "intent_nodes"

    id = Column(String, primary_key=True, default=gen_id)
    intent_code = Column(String, nullable=False, unique=True,
                         comment="Stable identifier, e.g. 'group-arch'")
    parent_code = Column(String, default=None, index=True,
                         comment="Parent intent_code; NULL for root")
    name = Column(String, nullable=False, comment="Display name")
    description = Column(String, default="", comment="Semantic hint for LLM")
    level = Column(Integer, default=2, comment="0=DOMAIN, 1=CATEGORY, 2=TOPIC")
    examples = Column(JSON, default=list, comment="Sample user questions")

    # Leaf binding: CC Switch provider id (from cc-switch.db providers.id).
    # Non-leaf nodes may also have a default provider; classifier can fall back.
    provider_id = Column(String, default=None,
                         comment="CC Switch provider UUID; only meaningful on leaves")

    sort_order = Column(Integer, default=0)
    enabled = Column(Integer, default=1)
    deleted = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


def _auto_bind_leaves(db: Session, leaves: list[IntentNode]) -> None:
    """Best-effort auto-binding of leaf nodes to CC Switch providers.

    Matches leaves to existing providers by name keywords (case-insensitive).
    Only fills `provider_id` when currently None — never overrides user choice.
    Silent no-op if CC Switch DB is unavailable or has no matching provider.
    """
    db_path = os.path.expanduser(r"~\.cc-switch\cc-switch.db")
    if not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name FROM providers "
            "WHERE name != 'default' ORDER BY is_current DESC, name"
        ).fetchall()
        conn.close()
    except Exception:
        return
    if not rows:
        return

    KEYWORDS = {
        "t-arch":   ["claude", "opus", "sonnet"],
        "t-bug":    ["claude", "opus", "sonnet"],
        "t-facts":  ["deepseek", "bailian", "minimax", "moonshot", "qwen"],
        "t-write":  ["deepseek", "bailian", "minimax", "moonshot", "qwen"],
    }
    name_lower = {r["name"].lower(): r["id"] for r in rows}

    for leaf in leaves:
        if leaf.provider_id:
            continue
        codes = KEYWORDS.get(leaf.intent_code, [])
        for kw in codes:
            hit = next((pid for nl, pid in name_lower.items() if kw in nl), None)
            if hit:
                leaf.provider_id = hit
                break


def seed_intent_tree(db: Session):
    """Seed a starter intent tree with three root domains.

    Leaves are auto-bound to existing CC Switch providers when possible
    (claude-family for hard tasks, deepseek/bailian for cheap ones). User
    can re-bind anything afterwards via the UI.
    """
    if db.query(IntentNode).count() > 0:
        return

    rows = [
        # ── Domain 1: Code & Architecture ───────────────────────
        IntentNode(id="d1", intent_code="d-code", name="代码与架构",
                   description="代码生成、重构、架构设计、调试", level=0,
                   examples=[], sort_order=10),
        IntentNode(id="d1-c1", intent_code="c-arch", parent_code="d-code",
                   name="架构设计", description="系统设计、技术选型、分布式方案",
                   level=1, examples=[], sort_order=10),
        IntentNode(id="d1-c1-t1", intent_code="t-arch", parent_code="c-arch",
                   name="复杂架构", description="需要深度推理的架构、分布式、微服务",
                   level=2,
                   examples=["设计一个分布式任务调度系统",
                             "如何拆分微服务",
                             "选型 Kafka 还是 RabbitMQ"],
                   sort_order=10),

        IntentNode(id="d1-c2", intent_code="c-bug", parent_code="d-code",
                   name="Bug 调试", description="报错分析、性能瓶颈、内存泄漏",
                   level=1, examples=[], sort_order=20),
        IntentNode(id="d1-c2-t1", intent_code="t-bug", parent_code="c-bug",
                   name="Bug 修复", description="具体错误定位与修复",
                   level=2,
                   examples=["这个报错怎么修",
                             "内存泄漏排查",
                             "为什么事务回滚失败"],
                   sort_order=10),

        # ── Domain 2: Quick Q&A ─────────────────────────────────
        IntentNode(id="d2", intent_code="d-qa", name="快速问答",
                   description="概念解释、API 用法、简单查询", level=0,
                   examples=[], sort_order=20),
        IntentNode(id="d2-c1", intent_code="c-facts", parent_code="d-qa",
                   name="常识 / 概念", description="解释名词、概念、原理",
                   level=1, examples=[], sort_order=10),
        IntentNode(id="d2-c1-t1", intent_code="t-facts", parent_code="c-facts",
                   name="概念解释", description="解释技术概念、API 用法",
                   level=2,
                   examples=["什么是 Redis 事务",
                             "Python 装饰器怎么用",
                             "TCP 三次握手过程"],
                   sort_order=10),

        # ── Domain 3: Documents / Writing ───────────────────────
        IntentNode(id="d3", intent_code="d-doc", name="文档写作",
                   description="写文档、注释、README、PR 描述", level=0,
                   examples=[], sort_order=30),
        IntentNode(id="d3-c1", intent_code="c-write", parent_code="d-doc",
                   name="写文档", description="生成 README、注释、API 文档",
                   level=1, examples=[], sort_order=10),
        IntentNode(id="d3-c1-t1", intent_code="t-write", parent_code="c-write",
                   name="文档生成", description="生成项目文档",
                   level=2,
                   examples=["给这个模块写 README",
                             "补全所有函数注释",
                             "写 PR 描述"],
                   sort_order=10),
    ]

    leaves = [n for n in rows if n.level == 2]
    _auto_bind_leaves(db, leaves)

    db.add_all(rows)
    db.commit()


def seed_demo_data(db: Session):
    """Insert sample request logs (for dashboard demo)."""
    if db.query(RequestLog).count() > 0:
        return

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
