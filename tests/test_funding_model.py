from src.funding_model import rank_opportunities, score_opportunity
from src.models import AccountConfig, FundingOpportunity


def test_score_returns_short_side_for_positive_funding():
    opportunity = FundingOpportunity("COINUSDT", 2.0, 20_000_000, 1.0, 0.8)
    result = score_opportunity(AccountConfig(), opportunity)
    assert result["suggested_side"] == "short_perp"
    assert result["projected_monthly_income_gbp"] > 0


def test_rank_orders_best_score_first():
    config = AccountConfig()
    opportunities = [
        FundingOpportunity("LOWUSDT", 0.20, 20_000_000, 1.0, 0.8),
        FundingOpportunity("HIGHUSDT", 1.20, 20_000_000, 1.0, 0.8),
    ]

    ranked = rank_opportunities(config, opportunities)

    assert ranked[0]["symbol"] == "HIGHUSDT"
