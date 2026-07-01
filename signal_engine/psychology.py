"""Qualitative + quantitative event psychology scoring.

The goal is not to make the bot more emotional. It is to convert a human
market-psychology read into structured inputs that can be backtested and
blocked by the same safety layer as every other trade.
"""

from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    USD_BULLISH = "usd_bullish"
    USD_BEARISH = "usd_bearish"
    NO_TRADE = "no_trade"


@dataclass(frozen=True)
class PsychologyEvent:
    event_name: str
    instrument: str
    actual: float
    forecast: float
    previous: float | None = None
    consensus_bias: float = 0.0
    positioning_crowding: float = 0.0
    narrative_strength: float = 0.5
    event_credibility: float = 1.0
    pre_event_drift: float = 0.0
    post_event_confirmation: float = 0.0
    volatility_regime: float = 0.5


@dataclass(frozen=True)
class PsychologyScore:
    event_name: str
    instrument: str
    direction: Direction
    surprise_score: float
    emotion_score: float
    conviction_score: float
    trade_permission: str
    reasons: tuple[str, ...]


def score_event(event: PsychologyEvent) -> PsychologyScore:
    surprise = compute_surprise(event.actual, event.forecast)
    direction = infer_direction(event, surprise)
    reasons: list[str] = []

    if direction == Direction.NO_TRADE:
        return PsychologyScore(
            event_name=event.event_name,
            instrument=event.instrument,
            direction=direction,
            surprise_score=round(surprise, 4),
            emotion_score=0.0,
            conviction_score=0.0,
            trade_permission="SKIP",
            reasons=("event has no clear psychological direction",),
        )

    surprise_magnitude = abs(surprise)
    crowding_boost = clamp(abs(event.positioning_crowding), 0.0, 1.0)
    narrative = clamp(event.narrative_strength, 0.0, 1.0)
    credibility = clamp(event.event_credibility, 0.0, 1.0)
    confirmation = clamp(event.post_event_confirmation, -1.0, 1.0)
    drift = clamp(event.pre_event_drift, -1.0, 1.0)
    volatility = clamp(event.volatility_regime, 0.0, 1.0)

    fade_risk = 0.0
    if sign(drift) == sign(surprise) and abs(drift) > 0.4:
        fade_risk += 0.20
        reasons.append("market moved in the event direction before release")
    if volatility > 0.85:
        fade_risk += 0.15
        reasons.append("volatility regime is high, so stop risk is elevated")
    if credibility < 0.5:
        fade_risk += 0.25
        reasons.append("event credibility is weak")

    emotion = (
        surprise_magnitude * 0.35
        + crowding_boost * 0.20
        + narrative * 0.20
        + credibility * 0.15
        + max(confirmation, 0.0) * 0.10
    )
    conviction = clamp(emotion - fade_risk, 0.0, 1.0)

    if surprise_magnitude < 0.05:
        reasons.append("surprise is too small")
    if confirmation < 0.15:
        reasons.append("price action has not confirmed the psychological read")
    if conviction >= 0.70:
        permission = "TRADE"
    elif conviction >= 0.50:
        permission = "WATCH"
    else:
        permission = "SKIP"

    if not reasons:
        reasons.append("surprise, narrative and confirmation are aligned")

    return PsychologyScore(
        event_name=event.event_name,
        instrument=event.instrument,
        direction=direction,
        surprise_score=round(surprise, 4),
        emotion_score=round(emotion, 4),
        conviction_score=round(conviction, 4),
        trade_permission=permission,
        reasons=tuple(reasons),
    )


def compute_surprise(actual: float, forecast: float) -> float:
    denominator = max(abs(forecast), 1.0)
    return clamp((actual - forecast) / denominator, -1.0, 1.0)


def infer_direction(event: PsychologyEvent, surprise: float) -> Direction:
    name = event.event_name.lower()
    if abs(surprise) < 0.03:
        return Direction.NO_TRADE

    hot_growth = any(key in name for key in ("nfp", "payroll", "jobs", "retail", "ism", "gdp"))
    hot_inflation = any(key in name for key in ("cpi", "pce", "inflation", "wage"))
    central_bank = any(key in name for key in ("fomc", "fed", "boe", "ecb", "rate"))

    if hot_inflation:
        return Direction.RISK_OFF if surprise > 0 else Direction.RISK_ON
    if hot_growth:
        return Direction.RISK_ON if surprise > 0 else Direction.RISK_OFF
    if central_bank:
        return Direction.USD_BULLISH if surprise > 0 else Direction.USD_BEARISH
    return Direction.RISK_ON if surprise > 0 else Direction.RISK_OFF


def position_size_multiplier(score: PsychologyScore) -> float:
    """Scale opportunity frequency without relaxing the GBP risk guard."""
    if score.trade_permission != "TRADE":
        return 0.0
    if score.conviction_score >= 0.85:
        return 1.0
    if score.conviction_score >= 0.75:
        return 0.75
    return 0.50


def sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
