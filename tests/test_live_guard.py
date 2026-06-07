from datetime import datetime, timedelta, timezone

from risk_engine.live_guard import (
    PilotConfig,
    RuntimeState,
    TradeProposal,
    activate_kill_switch,
    confirmation_phrase,
    evaluate_trade,
)


def proposal(now: datetime) -> TradeProposal:
    return TradeProposal(
        proposal_id="nfp-001",
        instrument="US500",
        direction="BUY",
        size=0.25,
        leverage=1.0,
        planned_loss_gbp=5.0,
        stop_distance=20.0,
        signal_created_at=now,
        market_data_at=now,
        calendar_updated_at=now,
        broker_order_key="nfp-001-us500-buy",
    )


def state() -> RuntimeState:
    return RuntimeState(
        equity_gbp=500.0,
        open_positions=0,
        daily_pnl_gbp=0.0,
        weekly_pnl_gbp=0.0,
        broker_connected=True,
        account_is_live=True,
    )


def test_exact_confirmation_allows_valid_trade():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    trade = proposal(now)
    decision = evaluate_trade(
        trade,
        state(),
        confirmation=confirmation_phrase(trade),
        now=now,
    )
    assert decision.allowed


def test_trade_is_blocked_without_manual_confirmation():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    decision = evaluate_trade(proposal(now), state(), now=now)
    assert not decision.allowed
    assert any("manual confirmation" in reason for reason in decision.blocked_by)


def test_stale_market_data_is_blocked():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    trade = proposal(now)
    stale = TradeProposal(
        **{**trade.__dict__, "market_data_at": now - timedelta(seconds=6)}
    )
    decision = evaluate_trade(
        stale,
        state(),
        confirmation=confirmation_phrase(stale),
        now=now,
    )
    assert not decision.allowed
    assert any("market data is stale" in reason for reason in decision.blocked_by)


def test_duplicate_order_is_blocked():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    trade = proposal(now)
    runtime = RuntimeState(
        **{**state().__dict__, "existing_order_keys": frozenset({trade.broker_order_key})}
    )
    decision = evaluate_trade(
        trade,
        runtime,
        confirmation=confirmation_phrase(trade),
        now=now,
    )
    assert not decision.allowed
    assert "duplicate broker order key" in decision.blocked_by


def test_loss_limit_and_leverage_are_blocked():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    trade = proposal(now)
    leveraged = TradeProposal(**{**trade.__dict__, "leverage": 2.0})
    losing_state = RuntimeState(**{**state().__dict__, "daily_pnl_gbp": -10.0})
    decision = evaluate_trade(
        leveraged,
        losing_state,
        confirmation=confirmation_phrase(leveraged),
        now=now,
    )
    assert not decision.allowed
    assert "daily loss limit reached" in decision.blocked_by
    assert "leverage is disabled for the pilot" in decision.blocked_by


def test_kill_switch_blocks_every_order():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    trade = proposal(now)
    killed = activate_kill_switch(state())
    decision = evaluate_trade(
        trade,
        killed,
        confirmation=confirmation_phrase(trade),
        now=now,
    )
    assert not decision.allowed
    assert "account kill switch is active" in decision.blocked_by
