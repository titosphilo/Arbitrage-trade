from .models import FundingOpportunity


SAMPLE_OPPORTUNITIES = [
    FundingOpportunity("COINUSDT", 2.26, 18_000_000, 1.45, 0.72, "stock_perp"),
    FundingOpportunity("AMZNUSDT", 1.38, 22_000_000, 0.72, 0.66, "stock_perp"),
    FundingOpportunity("CBRSUSDT", 0.89, 4_000_000, 1.25, 0.55, "stock_perp"),
    FundingOpportunity("METAUSDT", 0.62, 16_000_000, 0.68, 0.63, "stock_perp"),
    FundingOpportunity("BTCUSDT", 0.18, 800_000_000, 0.58, 0.80, "crypto"),
]
