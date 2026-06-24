"""RAgent Router's own provider selection state — instant, no restart needed."""

import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "provider_state.json")

DEFAULT_PROVIDER = "98aa7573-be9b-49b2-9a74-4e645e520f9e"  # DeepSeek


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"active_provider_id": DEFAULT_PROVIDER}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_active_provider_id() -> str:
    return load_state().get("active_provider_id", DEFAULT_PROVIDER)


def set_active_provider_id(provider_id: str):
    state = load_state()
    state["active_provider_id"] = provider_id
    save_state(state)
