"""Contract tests for the Impossibl provider profile.

Runs against a Hermes Agent checkout on ``PYTHONPATH`` (see the workflow) and
exercises the *real* discovery path: the plugin is copied into a temporary
``$HERMES_HOME/plugins/hermes-impossibl/`` exactly as ``hermes plugins install``
lays it out, then resolved through ``providers.get_provider_profile``.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
from pathlib import Path

import pytest

providers = pytest.importorskip("providers", reason="needs a hermes-agent checkout on PYTHONPATH")

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

CATALOG = {
    "object": "list",
    "data": [
        {"id": "anthropic/claude-sonnet-5", "endpoints": ["/v1/chat/completions"]},
        {"id": "openai/gpt-5.4-mini", "endpoints": ["/v1/chat/completions"], "supports_tools": True},
        {"id": "convaiinnovations/laya", "endpoints": ["/v1/chat/completions"], "supports_tools": False},
        {"id": "openai/gpt-image-2", "endpoints": ["/v1/images/generations"]},
        {"id": "openai/text-embedding-3-small", "endpoints": ["/v1/embeddings"]},
        {"id": "openai/whisper-large-v3", "endpoints": ["/v1/audio/transcriptions"]},
        {"id": "xai/grok-voice-tts-1.0", "endpoints": ["/v1/audio/speech"]},
        {"id": "typesafe-ai/jev", "endpoints": ["/v1/systemone"], "supports_tools": False},
    ],
}


def _reset_discovery() -> None:
    """Forget every registered profile and the imported user-plugin module so
    the next ``get_provider_profile`` call re-runs discovery from scratch."""
    providers._REGISTRY.clear()
    providers._ALIASES.clear()
    providers._PROVIDER_LIST_CACHE = None
    providers._discovered = False
    for name in [m for m in sys.modules if m.startswith("_hermes_user_provider_")]:
        sys.modules.pop(name, None)


@pytest.fixture
def impossibl_profile(tmp_path, monkeypatch):
    dest = tmp_path / "plugins" / "hermes-impossibl"
    dest.mkdir(parents=True)
    for name in ("__init__.py", "plugin.yaml"):
        shutil.copy(PLUGIN_ROOT / name, dest / name)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("IMPOSSIBL_BASE_URL", raising=False)
    _reset_discovery()
    profile = providers.get_provider_profile("impossibl")
    assert profile is not None, "impossibl profile must be discovered from $HERMES_HOME/plugins/hermes-impossibl"
    yield profile
    _reset_discovery()


@pytest.fixture
def served_catalog(monkeypatch):
    """Serve ``CATALOG`` to ``fetch_models`` and record the request it made."""
    import hermes_cli.urllib_security as urllib_security

    seen = {}

    def fake_open(req, timeout=None):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        return io.BytesIO(json.dumps(CATALOG).encode())

    monkeypatch.setattr(urllib_security, "open_credentialed_url", fake_open)
    return seen


class TestIdentity:
    def test_core_fields(self, impossibl_profile):
        p = impossibl_profile
        assert p.name == "impossibl"
        assert p.api_mode == "chat_completions"
        assert p.auth_type == "api_key"
        assert p.base_url == "https://api.impossibl.com/v1"
        assert p.env_vars == ("IMPOSSIBL_API_KEY", "IMPOSSIBL_BASE_URL")
        assert p.get_hostname() == "api.impossibl.com"

    def test_aliases_resolve(self, impossibl_profile):
        for alias in ("impossibl.com", "impossibl-ai"):
            assert providers.get_provider_profile(alias) is impossibl_profile

    def test_display_metadata(self, impossibl_profile):
        assert impossibl_profile.display_name == "Impossibl"
        assert impossibl_profile.description
        assert impossibl_profile.signup_url.startswith("https://")


class TestCatalog:
    def test_fallback_models_are_creator_scoped(self, impossibl_profile):
        assert impossibl_profile.fallback_models
        for model in impossibl_profile.fallback_models:
            creator, _, name = model.partition("/")
            assert creator and name, f"{model!r} must be a <creator>/<model> id"

    def test_aux_model_is_in_fallbacks(self, impossibl_profile):
        assert impossibl_profile.default_aux_model in impossibl_profile.fallback_models

    def test_fetch_models_keeps_only_tool_capable_chat_models(self, impossibl_profile, served_catalog):
        assert impossibl_profile.fetch_models(api_key="imp-test") == [
            "anthropic/claude-sonnet-5",
            "openai/gpt-5.4-mini",
        ]
        assert served_catalog["url"] == "https://api.impossibl.com/v1/models"
        assert served_catalog["auth"] == "Bearer imp-test"

    def test_fetch_models_honours_a_custom_base_url(self, impossibl_profile, served_catalog):
        impossibl_profile.fetch_models(base_url="https://api-staging.impossibl.com/v1/")
        assert served_catalog["url"] == "https://api-staging.impossibl.com/v1/models"

    def test_fetch_models_returns_none_on_failure(self, impossibl_profile, monkeypatch):
        import hermes_cli.urllib_security as urllib_security

        def boom(req, timeout=None):
            raise OSError("network down")

        monkeypatch.setattr(urllib_security, "open_credentialed_url", boom)
        assert impossibl_profile.fetch_models() is None


class TestListing:
    def test_listed_once(self, impossibl_profile):
        names = [p.name for p in providers.list_providers()]
        assert names.count("impossibl") == 1
