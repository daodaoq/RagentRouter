"""Anthropic-compatible POST /v1/messages endpoint."""

import uuid
import time
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas import MessagesRequest, MessagesResponse, ContentBlock, Usage
from services.rule_router import select_model
from services.provider_adapter import call_claude, call_deepseek, estimate_tokens
from services.analytics import log_request

router = APIRouter(prefix="/v1", tags=["Messages"])


@router.post("/messages")
async def create_message(
    body: MessagesRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """Anthropic Messages API compatible endpoint.

    Accepts the same JSON schema as Anthropic's /v1/messages.
    When model="auto", the rule router selects the best provider.
    """
    t0 = time.time()

    # Extract user text from messages
    user_text = ""
    system_text = ""
    if body.system:
        if isinstance(body.system, str):
            system_text = body.system
        elif isinstance(body.system, list):
            for block in body.system:
                if isinstance(block, dict) and block.get("type") == "text":
                    system_text += block.get("text", "")

    for msg in body.messages:
        if msg.role == "user":
            content = msg.content
            if isinstance(content, str):
                user_text += content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        user_text += block.get("text", "")
                    elif hasattr(block, "text"):
                        user_text += block.text or ""

    # ── Route decision ──
    # Convert MessagesRequest.messages (Pydantic models) to dicts for routing
    messages_dicts = []
    for m in body.messages:
        content = m.content
        if isinstance(content, list):
            content = [c.model_dump() if hasattr(c, "model_dump") else c for c in content]
        messages_dicts.append({"role": m.role, "content": content})

    if body.model == "auto":
        route = select_model(db, user_text, system_text)
    else:
        # Explicit model requested
        provider = "claude" if "claude" in body.model.lower() else "deepseek"
        route = {
            "provider": provider,
            "model": body.model,
            "rule_name": "User specified",
            "reason": f"Model explicitly set to {body.model}",
        }

    # ── Call provider ──
    if route["provider"] == "claude":
        result = await call_claude(system_text, messages_dicts, body.max_tokens, body.stream)
    elif route["provider"] == "deepseek":
        result = await call_deepseek(system_text, messages_dicts, body.max_tokens, body.stream)
    else:
        result = await call_deepseek(system_text, messages_dicts, body.max_tokens, body.stream)

    latency_ms = int((time.time() - t0) * 1000)

    # ── Streaming ──
    if body.stream:
        return StreamingResponse(
            _sse_generator(result["text"], route, result, latency_ms),
            media_type="text/event-stream",
            headers={
                "x-ragent-model": route["model"],
                "x-ragent-provider": route["provider"],
                "x-ragent-rule": route.get("rule_name", ""),
                "x-ragent-reason": route.get("reason", ""),
            },
        )

    # ── Log the request ──
    log_request(
        db,
        prompt=user_text[:500],
        prompt_tokens=result["input_tokens"],
        completion_tokens=result["output_tokens"],
        model=route["model"],
        provider=route["provider"],
        route_reason=route.get("reason", ""),
        latency_ms=latency_ms,
    )

    # ── Build Anthropic-compatible response ──
    msg_id = f"msg_{uuid.uuid4().hex[:16]}"
    return MessagesResponse(
        id=msg_id,
        model=route["model"],
        content=[ContentBlock(type="text", text=result["text"])],
        stop_reason="end_turn",
        usage=Usage(
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
        ),
    )


async def _sse_generator(text: str, route: dict, result: dict, latency_ms: int):
    """Generate SSE streaming events."""
    # Send message_start
    yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': f'msg_{uuid.uuid4().hex[:12]}', 'type': 'message', 'role': 'assistant', 'model': route['model']}})}\n\n"

    # Send content_block_start
    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

    # Stream text in chunks
    words = text.split()
    chunk_size = max(1, len(words) // 8)
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size]) + " "
        yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': chunk}})}\n\n"

    # Send content_block_stop
    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

    # Send message_delta with usage
    yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': result['output_tokens']}})}\n\n"

    # Send message_stop
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
