"""Token budgets from budgets.yaml (opt-in enforcement)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from construct_zero.home.paths import cz_state_dir


@dataclass
class BudgetConfig:
    enforce: bool = True
    defaults: dict[str, int] = field(default_factory=dict)
    agents: dict[str, dict[str, int]] = field(default_factory=dict)
    channel: dict[str, int] = field(default_factory=dict)


def budgets_path() -> Path:
    return cz_state_dir() / "budgets.yaml"


def load_budgets(path: Path | None = None) -> BudgetConfig | None:
    p = path or budgets_path()
    if not p.is_file():
        return None
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return BudgetConfig(
        enforce=bool(data.get("enforce", True)),
        defaults=dict(data.get("defaults") or {}),
        agents={k: dict(v) for k, v in (data.get("agents") or {}).items()},
        channel=dict(data.get("channel") or {}),
    )


def per_session_cap(cfg: BudgetConfig, agent: str) -> int | None:
    if agent in cfg.agents and "per_session_tokens" in cfg.agents[agent]:
        return int(cfg.agents[agent]["per_session_tokens"])
    if "per_session_tokens" in cfg.defaults:
        return int(cfg.defaults["per_session_tokens"])
    return None


def per_agent_daily_cap(cfg: BudgetConfig, agent: str) -> int | None:
    if agent in cfg.agents and "per_agent_daily_tokens" in cfg.agents[agent]:
        return int(cfg.agents[agent]["per_agent_daily_tokens"])
    if "per_agent_daily_tokens" in cfg.defaults:
        return int(cfg.defaults["per_agent_daily_tokens"])
    return None


def budget_error_message(agent: str, cap: int, scope: str) -> dict[str, Any]:
    msg = (
        f"Token cap reached for agent '{agent}' ({cap}/{scope}). "
        f"Fix: raise it in budgets.yaml or start a new session."
    )
    return {
        "error": {
            "message": msg,
            "type": "rate_limit_error",
            "code": "cz_budget_exceeded",
        },
        "detail": msg,
    }
