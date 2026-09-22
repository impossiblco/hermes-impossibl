"""Impossibl provider profile for Hermes Agent.

Impossibl (https://impossibl.com) is an AI gateway: 100+ models from OpenAI,
Anthropic, Google, xAI, DeepSeek, Moonshot, Z.ai, Qwen, MiniMax and more behind
one OpenAI-compatible API and one key. This plugin registers ``impossibl`` as a
first-class provider so ``hermes model``, ``--provider impossibl``,
``hermes doctor`` and the auxiliary-model defaults all work without touching
Hermes core.

Install::

    hermes plugins install impossiblco/hermes-impossibl --enable
    echo 'IMPOSSIBL_API_KEY=<your key>' >> ~/.hermes/.env
    hermes model            # pick "Impossibl", then a model

Model ids are ``<creator>/<model>``, e.g. ``anthropic/claude-sonnet-5`` or
``openai/gpt-5.5``. The live catalogue is ``https://api.impossibl.com/v1/models``.
"""

from __future__ import annotations

import json
import logging
import urllib.request

from providers import register_provider
from providers.base import ProviderProfile, _profile_user_agent

logger = logging.getLogger(__name__)

CHAT_ENDPOINT = "/v1/chat/completions"


def chat_model_ids(items: object) -> list[str]:
    """Ids from a ``/v1/models`` ``data`` array that Hermes can drive.

    The catalogue also lists image, speech, transcription, embedding and rerank
    models, each tagged with the ``endpoints`` it serves. Keep chat-completions
    models that do not declare ``supports_tools: false``. An entry without
    ``endpoints`` (a custom base URL serving a plain OpenAI list) is kept.
    """
    if not isinstance(items, list):
        return []
    ids = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        endpoints = item.get("endpoints")
        if isinstance(endpoints, list) and CHAT_ENDPOINT not in endpoints:
            continue
        if item.get("supports_tools") is False:
            continue
        ids.append(str(item["id"]))
    return list(dict.fromkeys(ids))


class ImpossiblProfile(ProviderProfile):
    """Impossibl — the default profile, with the picker limited to chat models."""

    def fetch_models(
        self, *, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0
    ) -> list[str] | None:
        from hermes_cli.urllib_security import open_credentialed_url

        url = ((base_url or "").strip() or self.base_url).rstrip("/") + "/models"
        req = urllib.request.Request(url)
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", _profile_user_agent())
        try:
            with open_credentialed_url(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            logger.debug("impossibl: catalog fetch failed: %s", exc)
            return None
        items = data if isinstance(data, list) else data.get("data")
        return chat_model_ids(items) or None


impossibl = ImpossiblProfile(
    name="impossibl",
    aliases=("impossibl.com", "impossibl-ai"),
    display_name="Impossibl",
    description="Impossibl — one OpenAI-compatible API for 100+ models from every major lab",
    signup_url="https://impossibl.com",
    # The trailing *_BASE_URL entry is Hermes' user override hook (docs: env_vars).
    env_vars=("IMPOSSIBL_API_KEY", "IMPOSSIBL_BASE_URL"),
    base_url="https://api.impossibl.com/v1",
    auth_type="api_key",
    # Cheap, tool- and vision-capable model for compression / titles / vision.
    default_aux_model="google/gemini-3.1-flash-lite",
    # Shown when the live /models fetch fails. Tool-calling chat models only,
    # verified against https://api.impossibl.com/v1/models on 2026-09-22.
    fallback_models=(
        "anthropic/claude-sonnet-5",
        "anthropic/claude-opus-5-5",
        "openai/gpt-5.5",
        "openai/gpt-5.4-mini",
        "google/gemini-3.8-flash",
        "google/gemini-3.1-flash-lite",
        "xai/grok-4.7",
        "deepseek/deepseek-v4-pro",
        "moonshotai/kimi-k3",
        "zai/glm-5.3",
        "minimaxai/minimax-m3",
    ),
)

register_provider(impossibl)
