"""Budget and kill checks for adapter inference."""

from __future__ import annotations

import json
import time
from typing import Any

from construct_zero.home import admin as admin_mod
from construct_zero.home import budgets as budgets_mod
from construct_zero.home import identity as identity_mod
from construct_zero.home import ledger as ledger_mod
from construct_zero.openai_types import ChatCompletionRequest


def killed_response() -> dict[str, Any]:
    return {
        "error": {
            "message": "Construct-Zero kill switch active. Run construct-zero unkill.",
            "type": "service_unavailable",
            "code": "cz_killed",
        },
        "detail": "cz_killed",
    }


def check_killed() -> dict[str, Any] | None:
    if admin_mod.is_killed():
        return killed_response()
    return None


def check_budget(
    agent: str,
    session: str | None,
    prompt_tokens: int,
    *,
    budgets_path=None,
    db_path=None,
) -> dict[str, Any] | None:
    cfg = budgets_mod.load_budgets(budgets_path)
    if cfg is None or not cfg.enforce:
        return None
    cap = budgets_mod.per_session_cap(cfg, agent)
    if cap is not None and session:
        used = ledger_mod.sum_tokens(agent=agent, session=session, db_path=db_path)
        if used + prompt_tokens > cap:
            return budgets_mod.budget_error_message(agent, cap, "session")
    daily = budgets_mod.per_agent_daily_cap(cfg, agent)
    if daily is not None:
        since = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime())
        used = ledger_mod.sum_tokens(agent=agent, since_ts=since, db_path=db_path)
        if used + prompt_tokens > daily:
            return budgets_mod.budget_error_message(agent, daily, "day")
    return None


def estimate_prompt_tokens(body: ChatCompletionRequest) -> int:
    blob = json.dumps([m.model_dump() for m in body.messages], ensure_ascii=False)
    return identity_mod.estimate_tokens(blob)


def record_adapter_usage(
    *,
    agent: str,
    session: str | None,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    request_id: str,
    status: int,
    db_path=None,
) -> None:
    ledger_mod.record_usage(
        agent=agent,
        session=session,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated=True,
        source="adapter",
        request_id=request_id,
        status=status,
        db_path=db_path,
    )
