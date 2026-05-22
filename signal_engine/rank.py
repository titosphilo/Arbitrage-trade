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


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
