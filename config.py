"""Central configuration for the arb research engine."""

# ── Data sources ──────────────────────────────────────────────────
BINANCE_BASE   = "https://fapi.binance.com/fapi/v1"
BINANCE_SPOT   = "https://api.binance.com/api/v3"
YAHOO_BASE     = "https://query1.finance.yahoo.com/v8/finance"

# ── Signal thresholds ─────────────────────────────────────────────
MIN_FUNDING_APR   = 15.0   # % — below this, exit or skip
ENTER_FUNDING_APR = 40.0   # % — above this, consider entry
STRONG_APR        = 80.0   # % — high conviction

MIN_OI_USD        = 500_000   # minimum open interest
MIN_VOLUME_USD    = 1_000_000 # minimum 24h volume

# ── Risk limits ───────────────────────────────────────────────────
MAX_POSITION_PCT  = 0.15   # 15% of account per position
MAX_PORTFOLIO_PCT = 0.70   # 70% total deployed
LIQUIDATION_BUFFER= 0.30   # 30% buffer before liquidation
MAX_CORRELATION   = 0.70   # max pairwise correlation

# ── Backtester ────────────────────────────────────────────────────
BACKTEST_DAYS    = 30
FUNDING_HAIRCUT  = 0.50    # 50% haircut on gross APR
SPREAD_COST_PCT  = 0.0004  # 0.04% round-trip
HEDGE_ERROR_PCT  = 0.05    # 5% basis error on hedge

# ── Paper portfolio ───────────────────────────────────────────────
PAPER_CAPITAL_GBP = 2000.0
GBP_USD_RATE      = 1.27

# ── Database ──────────────────────────────────────────────────────
DB_PATH = "data/arb_research.db"

# ── Stock perp hedge map ──────────────────────────────────────────
STOCK_PERP_HEDGES = {
    "COINUSDT":  {"stock": "COIN",  "etf": "BKCH",  "beta": 1.0},
    "AMZNUSDT":  {"stock": "AMZN",  "etf": "QQQ",   "beta": 1.1},
    "METAUSDT":  {"stock": "META",  "etf": "QQQ",   "beta": 1.2},
    "GOOGLUSDT": {"stock": "GOOGL", "etf": "QQQ",   "beta": 1.0},
    "NVDAUSDT":  {"stock": "NVDA",  "etf": "SMH",   "beta": 1.5},
    "QCOMUSDT":  {"stock": "QCOM",  "etf": "SMH",   "beta": 1.1},
    "MSFTUSDT":  {"stock": "MSFT",  "etf": "QQQ",   "beta": 0.9},
    "MRVLUSDT":  {"stock": "MRVL",  "etf": "SMH",   "beta": 1.3},
    "TSLAUSDT":  {"stock": "TSLA",  "etf": "ARKK",  "beta": 1.8},
    "INTCUSDT":  {"stock": "INTC",  "etf": "SMH",   "beta": 1.0},
}
