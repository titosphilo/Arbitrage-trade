"""Hard execution gate for a controlled GBP 500 trading pilot.

This module does not place orders. The live broker adapter must call
``evaluate_trade`` immediately before every order and refuse the order when
``allowed`` is false.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib


@dataclass(frozen=True)
class PilotConfig:
    starting_equity_gbp: float = 500.0
    max_risk_per_trade_gbp: float = 5.0
    max_daily_loss_gbp: float = 10.0
    max_weekly_loss_gbp: float = 20.0
    max_open_positions: int = 1
    max_leverage: float = 1.0
    max_market_data_age_seconds: int = 5
    max_signal_age_seconds: int = 15
    max_calendar_age_seconds: int = 900
    require_stop: bool = True
    require_manual_confirmation: bool = True


@dataclass(frozen=True)
class TradeProposal:
    proposal_id: str
    instrument: str
    direction: str
    size: float
    leverage: float
    planned_loss_gbp: float
    stop_distance: float
    signal_created_at: datetime
    market_data_at: datetime
    calendar_updated_at: datetime
    broker_order_key: str


@dataclass(frozen=True)
class RuntimeState:
    equity_gbp: float
    open_positions: int
    daily_pnl_gbp: float
    weekly_pnl_gbp: float
    existing_order_keys: frozenset[str] = field(default_factory=frozenset)
    kill_switch_active: bool = False
    broker_connected: bool = False
    account_is_live: bool = False


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    blocked_by: tuple[str, ...]
    warnings: tuple[str, ...]
    required_confirmation: str


def confirmation_phrase(proposal: TradeProposal) -> str:
    payload = (
        f"{proposal.proposal_id}|{proposal.instrument}|{proposal.direction}|"
        f"{proposal.size}|{proposal.planned_loss_gbp}|{proposal.broker_order_key}"
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8].upper()
    return f"CONFIRM-LIVE-{proposal.proposal_id}-{digest}"


def evaluate_trade(
    proposal: TradeProposal,
    state: RuntimeState,
    *,
    config: PilotConfig = PilotConfig(),
    confirmation: str | None = None,
    now: datetime | None = None,
) -> GuardDecision:
    now = now or datetime.now(timezone.utc)
    blocked: list[str] = []
    warnings: list[str] = []
    required_confirmation = confirmation_phrase(proposal)

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    if state.kill_switch_active:
        blocked.append("account kill switch is active")
    if not state.broker_connected:
        blocked.append("broker connection is not healthy")
    if not state.account_is_live:
        blocked.append("broker session is not confirmed as the intended live account")
    if state.equity_gbp <= 0:
        blocked.append("account equity is unavailable")
    if state.equity_gbp < config.starting_equity_gbp * 0.80:
        blocked.append("account equity is below the pilot floor")
    if state.open_positions >= config.max_open_positions:
        blocked.append("maximum open positions reached")
    if state.daily_pnl_gbp <= -config.max_daily_loss_gbp:
        blocked.append("daily loss limit reached")
    if state.weekly_pnl_gbp <= -config.max_weekly_loss_gbp:
        blocked.append("weekly loss limit reached")
    if proposal.planned_loss_gbp <= 0:
        blocked.append("planned loss must be positive")
    if proposal.planned_loss_gbp > config.max_risk_per_trade_gbp:
        blocked.append("planned loss exceeds GBP 5 pilot limit")
    if proposal.leverage > config.max_leverage:
        blocked.append("leverage is disabled for the pilot")
    if proposal.size <= 0:
        blocked.append("order size must be positive")
    if config.require_stop and proposal.stop_distance <= 0:
        blocked.append("a protective stop is required")
    if not proposal.broker_order_key:
        blocked.append("broker idempotency key is required")
    elif proposal.broker_order_key in state.existing_order_keys:
        blocked.append("duplicate broker order key")

    ages = {
        "market data": (now - proposal.market_data_at).total_seconds(),
        "signal": (now - proposal.signal_created_at).total_seconds(),
        "calendar": (now - proposal.calendar_updated_at).total_seconds(),
    }
    limits = {
        "market data": config.max_market_data_age_seconds,
        "signal": config.max_signal_age_seconds,
        "calendar": config.max_calendar_age_seconds,
    }
    for name, age in ages.items():
        if age < 0:
            blocked.append(f"{name} timestamp is in the future")
        elif age > limits[name]:
            blocked.append(f"{name} is stale ({age:.0f}s old)")

    if config.require_manual_confirmation and confirmation != required_confirmation:
        blocked.append("manual confirmation does not match this exact proposal")

    if proposal.planned_loss_gbp > state.equity_gbp * 0.01:
        warnings.append("planned loss is above 1% of current equity")

    return GuardDecision(
        allowed=not blocked,
        blocked_by=tuple(blocked),
        warnings=tuple(warnings),
        required_confirmation=required_confirmation,
    )


def activate_kill_switch(state: RuntimeState) -> RuntimeState:
    """Return a new runtime state that blocks all subsequent orders."""
    return RuntimeState(
        equity_gbp=state.equity_gbp,
        open_positions=state.open_positions,
        daily_pnl_gbp=state.daily_pnl_gbp,
        weekly_pnl_gbp=state.weekly_pnl_gbp,
        existing_order_keys=state.existing_order_keys,
        kill_switch_active=True,
        broker_connected=state.broker_connected,
        account_is_live=state.account_is_live,
    )
