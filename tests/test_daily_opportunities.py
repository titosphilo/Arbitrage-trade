from signal_engine.daily_opportunities import (
    DailySetup,
    DailySnapshot,
    rank_daily_opportunities,
    score_daily_opportunity,
)


def test_confirmed_daily_momentum_can_trade():
    opportunity = score_daily_opportunity(
        DailySnapshot(
            instrument="US500",
            overnight_return=0.012,
            intraday_range_pct=0.012,
            realized_volatility=0.018,
            vix_change=-0.04,
            dxy_change=-0.02,
            yield_change=-0.01,
            news_sentiment=0.8,
            positioning_crowding=-0.5,
            price_confirmation=0.8,
            liquidity_score=1.0,
        )
    )

    assert opportunity.setup == DailySetup.MOMENTUM
    assert opportunity.permission == "TRADE"
    assert opportunity.direction == "long"
    assert opportunity.risk_multiplier > 0


def test_sticky_high_funding_can_trade_as_daily_carry():
    opportunity = score_daily_opportunity(
        DailySnapshot(
            instrument="RAVEUSDT",
            funding_apr=75.0,
            sticky_probability=0.86,
            realized_volatility=0.015,
            news_sentiment=0.2,
            positioning_crowding=0.5,
            price_confirmation=0.7,
            liquidity_score=0.9,
        )
    )

    assert opportunity.setup == DailySetup.FUNDING_CARRY
    assert opportunity.permission == "TRADE"
    assert opportunity.direction == "short_perp"


def test_mixed_daily_noise_is_skipped():
    opportunity = score_daily_opportunity(
        DailySnapshot(
            instrument="GBPUSD",
            overnight_return=0.001,
            intraday_range_pct=0.002,
            realized_volatility=0.012,
            news_sentiment=0.1,
            positioning_crowding=0.1,
            price_confirmation=0.1,
            liquidity_score=1.0,
        )
    )

    assert opportunity.setup == DailySetup.NO_TRADE
    assert opportunity.permission == "SKIP"


def test_unconfirmed_setup_is_watch_or_skip_not_trade():
    opportunity = score_daily_opportunity(
        DailySnapshot(
            instrument="EURUSD",
            overnight_return=-0.015,
            intraday_range_pct=0.012,
            realized_volatility=0.02,
            news_sentiment=-0.8,
            positioning_crowding=0.8,
            price_confirmation=0.2,
            liquidity_score=1.0,
        )
    )

    assert opportunity.permission in {"WATCH", "SKIP"}
    assert opportunity.risk_multiplier == 0


def test_rank_daily_opportunities_orders_by_score():
    weak = DailySnapshot(instrument="WEAK", price_confirmation=0.1)
    strong = DailySnapshot(
        instrument="STRONG",
        funding_apr=80,
        sticky_probability=0.9,
        price_confirmation=0.8,
        liquidity_score=1.0,
    )

    ranked = rank_daily_opportunities([weak, strong])

    assert ranked[0].instrument == "STRONG"
