from dataclasses import dataclass

from signal_engine.persistence import PersistenceClassifier, PersistenceSample


@dataclass(frozen=True)
class EdgeCandidate:
    symbol: str
    funding_apr: float
    rate_volatility: float
    consecutive_positive_periods: float
    oi_change_rate: float
    coin_category: str
    liquidity_score: float = 1.0


@dataclass(frozen=True)
class RankedEdge:
    symbol: str
    edge_score: float
    sticky_probability: float
    funding_component: float
    persistence_component: float
    risk_penalty: float


def compute_edge_score(
    candidate: EdgeCandidate,
    persistence_classifier: PersistenceClassifier | None = None,
    *,
    sticky_probability: float | None = None,
) -> RankedEdge:
    if sticky_probability is None:
        if persistence_classifier is None:
            sticky_probability = 0.50
        else:
            sticky_probability = persistence_classifier.predict_probability(
                PersistenceSample(
                    symbol=candidate.symbol,
                    rate_volatility=candidate.rate_volatility,
                    consecutive_positive_periods=candidate.consecutive_positive_periods,
                    oi_change_rate=candidate.oi_change_rate,
                    coin_category=candidate.coin_category,
                    survival_rate=0.0,
                )
            )

    funding_component = clamp(candidate.funding_apr / 1.50, 0.0, 1.5)
    persistence_component = clamp(sticky_probability, 0.0, 1.0)
    streak_component = clamp(candidate.consecutive_positive_periods / 90, 0.0, 1.0)
    oi_component = clamp((candidate.oi_change_rate + 0.25) / 0.50, 0.0, 1.0)
    liquidity_component = clamp(candidate.liquidity_score, 0.0, 1.0)
    risk_penalty = clamp(candidate.rate_volatility / 0.50, 0.0, 1.0)

    score = (
        35 * funding_component
        + 35 * persistence_component
        + 12 * streak_component
        + 8 * oi_component
        + 10 * liquidity_component
        - 20 * risk_penalty
    )

    return RankedEdge(
        symbol=candidate.symbol,
        edge_score=round(score, 4),
        sticky_probability=round(sticky_probability, 4),
        funding_component=round(funding_component, 4),
        persistence_component=round(persistence_component, 4),
        risk_penalty=round(risk_penalty, 4),
    )


def rank_edges(
    candidates: list[EdgeCandidate],
    persistence_classifier: PersistenceClassifier | None = None,
) -> list[RankedEdge]:
    ranked = [
        compute_edge_score(candidate, persistence_classifier)
        for candidate in candidates
    ]
    return sorted(ranked, key=lambda edge: edge.edge_score, reverse=True)


def compute_score(
    *,
    ann_pct: float,
    persistence: float,
    volume_usd: float,
    oi_usd: float,
    ls_ratio: float,
    flip_risk: float,
) -> float:
    """Compatibility score for the original scanner API (0-100)."""
    apr_score = clamp((ann_pct - 15.0) / 65.0, 0.0, 1.0) * 35
    persistence_score = clamp(persistence, 0.0, 1.0) * 30
    volume_score = clamp(volume_usd / 5_000_000, 0.0, 1.0) * 15
    oi_score = clamp(oi_usd / 2_000_000, 0.0, 1.0) * 10
    crowding_score = clamp((ls_ratio - 1.0) / 1.0, 0.0, 1.0) * 10
    flip_penalty = clamp(flip_risk, 0.0, 1.0) * 20
    return round(
        clamp(
            apr_score
            + persistence_score
            + volume_score
            + oi_score
            + crowding_score
            - flip_penalty,
            0.0,
            100.0,
        ),
        2,
    )


def classify(score: float, ann_pct: float) -> str:
    """Compatibility classifier used by the original scanner and tests."""
    if ann_pct < 15:
        return "EXIT"
    if ann_pct >= 40 and score >= 70:
        return "ENTER"
    if score >= 45:
        return "WATCH"
    return "SKIP"


def estimate_flip_risk(history: list[float]) -> float:
    """Estimate sign-flip risk from a sequence of funding observations."""
    if len(history) < 2:
        return 0.5
    nonzero = [value for value in history if value != 0]
    if len(nonzero) < 2:
        return 0.5
    sign_changes = sum(
        1
        for previous, current in zip(nonzero, nonzero[1:])
        if (previous > 0) != (current > 0)
    )
    change_rate = sign_changes / (len(nonzero) - 1)
    negative_share = sum(value < 0 for value in nonzero) / len(nonzero)
    return round(clamp(change_rate * 0.8 + negative_share * 0.2, 0.0, 1.0), 4)


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
