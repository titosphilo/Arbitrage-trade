from signal_engine.psychology import Direction, PsychologyEvent, position_size_multiplier, score_event


def test_hot_cpi_creates_risk_off_trade_when_confirmed():
    score = score_event(
        PsychologyEvent(
            event_name="US CPI",
            instrument="US500",
            actual=3.6,
            forecast=3.0,
            positioning_crowding=-0.6,
            narrative_strength=0.9,
            event_credibility=1.0,
            post_event_confirmation=0.8,
            volatility_regime=0.4,
        )
    )

    assert score.direction == Direction.RISK_OFF
    assert score.trade_permission == "TRADE"
    assert position_size_multiplier(score) > 0


def test_inline_event_is_skipped():
    score = score_event(
        PsychologyEvent(
            event_name="US NFP",
            instrument="US500",
            actual=202_000,
            forecast=200_000,
            post_event_confirmation=0.8,
        )
    )

    assert score.direction == Direction.NO_TRADE
    assert score.trade_permission == "SKIP"


def test_no_confirmation_blocks_trade_even_with_surprise():
    score = score_event(
        PsychologyEvent(
            event_name="US CPI",
            instrument="US500",
            actual=3.8,
            forecast=3.0,
            positioning_crowding=-0.6,
            narrative_strength=0.9,
            event_credibility=1.0,
            post_event_confirmation=0.0,
        )
    )

    assert score.trade_permission in {"WATCH", "SKIP"}
    assert position_size_multiplier(score) == 0


def test_pre_event_drift_reduces_conviction():
    clean = score_event(
        PsychologyEvent(
            event_name="US Retail Sales",
            instrument="US500",
            actual=1.4,
            forecast=1.0,
            positioning_crowding=0.7,
            narrative_strength=0.8,
            event_credibility=1.0,
            pre_event_drift=0.0,
            post_event_confirmation=0.9,
        )
    )
    crowded = score_event(
        PsychologyEvent(
            event_name="US Retail Sales",
            instrument="US500",
            actual=1.4,
            forecast=1.0,
            positioning_crowding=0.7,
            narrative_strength=0.8,
            event_credibility=1.0,
            pre_event_drift=0.8,
            post_event_confirmation=0.9,
        )
    )

    assert crowded.conviction_score < clean.conviction_score
