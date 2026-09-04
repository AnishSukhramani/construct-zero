"""Construct-Zero model provider — points Hermes at the local Cursor adapter."""

from __future__ import annotations

from providers import register_provider
from providers.base import ProviderProfile

construct_zero = ProviderProfile(
    name="construct-zero",
    aliases=("hcx", "hermesxcursor", "hcx-cursor", "cz", "cursor"),
    display_name="Construct-Zero (Cursor via local adapter)",
    description=(
        "Routes Hermes inference through the Construct-Zero adapter on localhost, "
        "billing Cursor subscription models (auto / composer / …). "
        "Start the adapter first: scripts/start-adapter.sh"
    ),
    signup_url="https://cursor.com/dashboard/api",
    env_vars=("CZ_API_KEY", "CZ_BASE_URL", "HCX_API_KEY", "HCX_BASE_URL"),
    base_url="http://127.0.0.1:8765/v1",
    auth_type="api_key",
    api_mode="chat_completions",
    default_aux_model="auto",
    fallback_models=("auto", "composer-2.5", "composer-2.5-fast"),
)

register_provider(construct_zero)
