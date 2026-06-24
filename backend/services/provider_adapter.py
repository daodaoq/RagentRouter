import asyncio
import uuid
from typing import AsyncIterator

from config import settings


# ── Cost rates per 1M tokens ──────────────────────────────────────

COST_RATES = {
    "claude": {"input": 3.0, "output": 15.0},
    "deepseek": {"input": 0.27, "output": 1.10},
}


def calculate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_RATES.get(provider, {"input": 0, "output": 0})
    cost = (input_tokens / 1_000_000) * rates["input"] + (
        output_tokens / 1_000_000
    ) * rates["output"]
    return round(cost, 6)


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return max(1, len(text) // 4)


# ── Mock responses ─────────────────────────────────────────────────

MOCK_RESPONSES: dict[str, dict[str, str]] = {
    "claude": {
        "Explain Redis": "Redis (Remote Dictionary Server) is an open-source, in-memory data structure store "
        "used as a database, cache, message broker, and queue. It supports various data structures "
        "such as strings, hashes, lists, sets, sorted sets, bitmaps, hyperloglogs, and geospatial indexes. "
        "Redis is known for its high performance, replication, and automatic partitioning capabilities.",
        "default": "This is a mock response from **Claude**. In production, this would be a real AI-generated "
        "response. The demo shows how RAgent Router intelligently chose Claude for this complex task "
        "based on routing rules.",
    },
    "deepseek": {
        "Explain Redis": "Redis 是一个开源的内存数据结构存储系统，可用作数据库、缓存、消息中间件和队列。"
        "它支持多种数据结构，如字符串、哈希、列表、集合、有序集合等。"
        "Redis 以高性能、持久化和高可用性而闻名，广泛应用于实时分析、会话管理、排行榜等场景。",
        "default": "这是来自 **DeepSeek** 的模拟响应。在正式环境中，这将由 DeepSeek 真实生成。"
        "RAgent Router 根据路由规则判断这是一个简单任务，自动选择了成本更低的 DeepSeek。",
    },
    "claude_stream": {
        "Explain Redis": [
            "Redis is an open-source, ",
            "in-memory data structure store ",
            "used as a database, cache, and message broker. ",
            "It supports strings, hashes, lists, sets, and more.",
        ],
        "default": [
            "This is a streaming mock response ",
            "from Claude (via RAgent Router). ",
            "The router selected Claude based on task complexity analysis.",
        ],
    },
    "deepseek_stream": {
        "Explain Redis": [
            "Redis 是一个开源的，",
            "内存中的数据结构存储系统，",
            "可用作数据库、缓存和消息代理。",
            "它支持字符串、哈希、列表、集合等数据结构。",
        ],
        "default": [
            "这是来自 DeepSeek 的流式模拟响应。",
            "RAgent Router 自动选择了 DeepSeek，",
            "因为它判断这是一个简单任务。",
        ],
    },
}


def _get_mock_key(user_content: str) -> str:
    """Find the best matching mock key for the user's message."""
    for key in MOCK_RESPONSES["claude"]:
        if key.lower() in user_content.lower():
            return key
    return "default"


# ── Adapter interface ──────────────────────────────────────────────


async def call_claude(
    system_prompt: str | None,
    messages: list[dict],
    max_tokens: int,
    stream: bool = False,
) -> dict:
    """Call Claude API. Uses mock in demo mode."""
    if settings.demo_mode:
        return await _mock_call("claude", messages, max_tokens, stream)

    # Real API call would go here
    # import anthropic
    # client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    # ...
    raise NotImplementedError("Real Claude API not configured. Set demo_mode=true or provide API key.")


async def call_deepseek(
    system_prompt: str | None,
    messages: list[dict],
    max_tokens: int,
    stream: bool = False,
) -> dict:
    """Call DeepSeek API. Uses mock in demo mode."""
    if settings.demo_mode:
        return await _mock_call("deepseek", messages, max_tokens, stream)

    raise NotImplementedError("Real DeepSeek API not configured. Set demo_mode=true or provide API key.")


async def _mock_call(
    provider: str,
    messages: list[dict],
    max_tokens: int,
    stream: bool = False,
) -> dict:
    """Generate mock response with realistic latency."""
    await _simulate_latency(provider)

    user_content = ""
    for m in messages:
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str):
                user_content = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        user_content += block.get("text", "")

    mock_key = _get_mock_key(user_content)

    stream_key = f"{provider}_stream"
    if stream and stream_key in MOCK_RESPONSES:
        chunks = MOCK_RESPONSES[stream_key].get(mock_key, MOCK_RESPONSES[stream_key]["default"])
        text = "".join(chunks)
    else:
        text = MOCK_RESPONSES[provider].get(mock_key, MOCK_RESPONSES[provider]["default"])

    input_tokens = estimate_tokens(user_content)
    output_tokens = estimate_tokens(text)

    return {
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": _model_name(provider),
        "stream_chunks": MOCK_RESPONSES.get(f"{provider}_stream", {}).get(mock_key, ["Mock response."])
        if stream
        else None,
    }


async def _simulate_latency(provider: str):
    """Simulate network latency."""
    delay = 0.3 if provider == "deepseek" else 0.8
    await asyncio.sleep(delay)


def _model_name(provider: str) -> str:
    if provider == "claude":
        return settings.default_claude_model
    return settings.default_deepseek_model


async def stream_response(provider: str, messages: list[dict], max_tokens: int) -> AsyncIterator[str]:
    """Generator for SSE streaming response."""
    result = await _mock_call(provider, messages, max_tokens, stream=True)
    chunks = result.get("stream_chunks", ["Streaming response."])
    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.1)


def call_provider(
    provider: str,
    system_prompt: str | None,
    messages: list[dict],
    max_tokens: int,
    stream: bool = False,
) -> dict:
    """Dispatch to the correct provider adapter."""
    import asyncio

    if provider == "claude":
        return asyncio.get_event_loop().run_until_complete(
            call_claude(system_prompt, messages, max_tokens, stream)
        )
    elif provider == "deepseek":
        return asyncio.get_event_loop().run_until_complete(
            call_deepseek(system_prompt, messages, max_tokens, stream)
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
