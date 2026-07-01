"""Daily opportunity scoring from always-available market data.

This module is for finding more *candidate* trades, not forcing activity.
It combines quantitative daily market structure with qualitative psychology
inputs and returns TRADE / WATCH / SKIP.
"""

from dataclasses import dataclass
from enum import Enum


class DailySetup(str, Enum):
    MOMENTUM = "momentum_continuation"
    MEAN_REVERSION = "mean_reversion"
    FUNDING_CARRY = "funding_carry"
    NO_TRADE = "no_trade"


@dataclass(frozen=True)
class DailySnapshot:
    instrument: str
    overnight_return: float = 0.0
    intraday_range_pct: float = 0.0
    realized_volatility: float = 0.0
    vix_change: float = 0.0
    dxy_change: float = 0.0
    yield_change: float = 0.0
    funding_apr: float = 0.0
    sticky_probability: float = 0.0
    news_sentiment: float = 0.0
    positioning_crowding: float = 0.0
    price_confirmation: float = 0.0
    liquidity_score: float = 1.0


@dataclass(frozen=True)
class DailyOpportunity:
    instrument: str
    setup: DailySetup
    permission: str
    score: float
    direction: str
    risk_multiplier: float
    reasons: tuple[str, ...]


def score_daily_opportunity(snapshot: DailySnapshot) -> DailyOpportunity:
    momentum_pressure = clamp(
        abs(snapshot.overnight_return) * 8
        + snapshot.intraday_range_pct * 4
        + max(snapshot.price_confirmation, 0.0) * 0.35,
        0.0,
        1.0,
    )
    macro_pressure = clamp(
        abs(snapshot.vix_change) * 3
        + abs(snapshot.dxy_change) * 4
        + abs(snapshot.yield_change) * 5,
        0.0,
        1.0,
    )
    psychology_pressure = clamp(
        abs(snapshot.news_sentiment) * 0.45
        + abs(snapshot.positioning_crowding) * 0.30
        + max(snapshot.price_confirmation, 0.0) * 0.25,
        0.0,
        1.0,
    )
    funding_pressure = clamp(
        abs(snapshot.funding_apr) / 80 * 0.65
        + snapshot.sticky_probability * 0.35,
        0.0,
        1.0,
    )
    vol_penalty = clamp(snapshot.realized_volatility / 0.04, 0.0, 1.0) * 0.25
    liquidity_penalty = (1.0 - clamp(snapshot.liquidity_score, 0.0, 1.0)) * 0.35

    setup = choose_setup(snapshot, momentum_pressure, funding_pressure)
    if setup == DailySetup.NO_TRADE:
        return DailyOpportunity(
            instrument=snapshot.instrument,
            setup=setup,
            permission="SKIP",
            score=0.0,
            direction="flat",
            risk_multiplier=0.0,
            reasons=("no daily edge is dominant",),
        )

    raw_score = (
        momentum_pressure * 0.30
        + macro_pressure * 0.15
        + psychology_pressure * 0.25
        + funding_pressure * 0.20
        + clamp(snapshot.price_confirmation, 0.0, 1.0) * 0.10
        - vol_penalty
        - liquidity_penalty
    )
    score = clamp(raw_score, 0.0, 1.0)
    reasons = explain(snapshot, setup, momentum_pressure, funding_pressure, macro_pressure)

    if score >= 0.68 and snapshot.price_confirmation >= 0.45 and snapshot.liquidity_score >= 0.60:
        permission = "TRADE"
    elif score >= 0.48:
        permission = "WATCH"
    else:
        permission = "SKIP"

    return DailyOpportunity(
        instrument=snapshot.instrument,
        setup=setup,
        permission=permission,
        score=round(score, 4),
        direction=infer_direction(snapshot, setup),
        risk_multiplier=risk_multiplier(score, permission),
        reasons=tuple(reasons),
    )


def choose_setup(
    snapshot: DailySnapshot,
    momentum_pressure: float,
    funding_pressure: float,
) -> DailySetup:
    if abs(snapshot.funding_apr) >= 40 and snapshot.sticky_probability >= 0.70:
        return DailySetup.FUNDING_CARRY
    if momentum_pressure >= 0.55 and snapshot.price_confirmation >= 0.35:
        return DailySetup.MOMENTUM
    if (
        abs(snapshot.positioning_crowding) >= 0.70
        and abs(snapshot.news_sentiment) >= 0.50
        and snapshot.price_confirmation >= 0.45
    ):
        return DailySetup.MEAN_REVERSION
    if funding_pressure >= 0.70 and abs(snapshot.funding_apr) >= 25:
        return DailySetup.FUNDING_CARRY
    return DailySetup.NO_TRADE


def infer_direction(snapshot: DailySnapshot, setup: DailySetup) -> str:
    if setup == DailySetup.FUNDING_CARRY:
        return "short_perp" if snapshot.funding_apr > 0 else "long_perp"
    if setup == DailySetup.MEAN_REVERSION:
        if snapshot.positioning_crowding > 0:
            return "fade_long_crowd"
        return "fade_short_crowd"
    if setup == DailySetup.MOMENTUM:
        if snapshot.overnight_return > 0 or snapshot.news_sentiment > 0:
            return "long"
        return "short"
    return "flat"


def risk_multiplier(score: float, permission: str) -> float:
    if permission != "TRADE":
        return 0.0
    if score >= 0.85:
        return 1.0
    if score >= 0.75:
        return 0.75
    return 0.50


def explain(
    snapshot: DailySnapshot,
    setup: DailySetup,
    momentum_pressure: float,
    funding_pressure: float,
    macro_pressure: float,
) -> list[str]:
    reasons: list[str] = [f"dominant setup: {setup.value}"]
    if momentum_pressure >= 0.55:
        reasons.append("daily momentum and price confirmation are aligned")
    if funding_pressure >= 0.70:
        reasons.append("funding carry is strong and persistent")
    if macro_pressure >= 0.50:
        reasons.append("macro pressure is active")
    if snapshot.realized_volatility > 0.04:
        reasons.append("realized volatility is high, reduce size")
    if snapshot.liquidity_score < 0.60:
        reasons.append("liquidity is weak")
    return reasons


def rank_daily_opportunities(snapshots: list[DailySnapshot]) -> list[DailyOpportunity]:
    scored = [score_daily_opportunity(snapshot) for snapshot in snapshots]
    return sorted(scored, key=lambda item: item.score, reverse=True)


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
