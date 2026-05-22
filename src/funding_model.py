from .models import AccountConfig, FundingOpportunity
from .risk import max_position_notional_gbp, monthly_funding_income_gbp, risk_flags


def score_opportunity(config: AccountConfig, opportunity: FundingOpportunity) -> dict:
    flags = risk_flags(config, opportunity)
    position_gbp = max_position_notional_gbp(config, opportunity)
    monthly_income_gbp = monthly_funding_income_gbp(position_gbp, opportunity.funding_apr)

    liquidity_score = min(opportunity.daily_volume_usd / 50_000_000, 1.0)
    volatility_penalty = min(opportunity.annualized_volatility / config.max_annualized_volatility, 1.5)
    raw_score = (
        opportunity.funding_apr * 50
        + opportunity.funding_persistence * 30
        + liquidity_score * 20
        - volatility_penalty * 20
        - len(flags) * 10
    )

    return {
        "symbol": opportunity.symbol,
        "category": opportunity.category,
        "funding_apr": opportunity.funding_apr,
        "score": round(raw_score, 2),
        "suggested_side": "short_perp" if opportunity.funding_apr > 0 else "skip",
        "max_position_gbp": position_gbp,
        "projected_monthly_income_gbp": monthly_income_gbp,
        "risk_flags": flags,
    }


def rank_opportunities(
    config: AccountConfig, opportunities: list[FundingOpportunity]
) -> list[dict]:
    scored = [score_opportunity(config, item) for item in opportunities]
    return sorted(scored, key=lambda item: item["score"], reverse=True)
