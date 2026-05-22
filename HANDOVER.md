# Handover Document — Funding Arbitrage Research Engine

**From:** Claude (Anthropic) — infrastructure, data collection, strategy research  
**To:** Codex (OpenAI) — model architecture, backtesting, ML signal refinement  
**Date:** 22 May 2026  
**Repo:** arb-research  

---

## Context

We have been building a research-first trading system for 12 days. The system is running live on a VPS (`72.62.212.97`) collecting real data. This repo is the research layer — no live trading until edges are proven.

## What already exists (live on VPS)

### Data collected
- `btc_price_1m` — 15,840+ Bitcoin 1-minute prices
- `gold_price_1m` — 15,840+ Gold 1-minute prices
- `funding_history` — 166 days × 100 coins = 42,000+ funding rate records
- `coin_profiles` — sticky score, avg rate, volatility for 100 coins
- `macro_snapshot` — VIX, DXY, 10Y yields every 5 minutes
- `ai_oracle_log` — 5-model AI consensus every 4 hours (28 readings)
- `btc_gold_monitor` — BTC/Gold ratio, Z-score, funding, macro score every 4h

### Key findings
1. **Sticky coins are real** — 15 coins paid positive every 8h period over 166 days. Sticky score ≥ 80 predicts persistence correctly.
2. **Gold/BTC correlation = -0.07** — they are independent markets (validated with 11 days of 1-min data)
3. **CPI/NFP direction is 13/13 correct** — HOT print → S&P falls, COOL print → S&P rises
4. **Stock perp rates** — COINUSDT 140%/yr, AMZNUSDT 130%/yr, METAUSDT 80%/yr (live right now)
5. **Oracle tracks BTC** — MEDIUM call on 11 May preceded 1.78% BTC drop next day

### What's running (PM2 processes)
```
funding-arb       — paper funding arb, 9 positions, £3.33 collected
ai-oracle         — 5-model consensus every 4h
event-trader      — CPI/NFP/FOMC directional trader (demo pending activation)
macro-monitor     — VIX/DXY/yields every 5min
btc-gold-monitor  — BTC/Gold pairs trade score every 4h
gold-straddle     — Gold mean-reversion (paused, wrong regime)
stock-perp        — Stock perp rate scanner every 4h
```

### Database location
```
/root/.openclaw/workspace/projects/trading-bot/trading_data.db (SQLite)
```
Tables: `funding_positions`, `funding_history`, `coin_profiles`, `btc_price_1m`, `gold_price_1m`, `ai_oracle_log`, `macro_snapshot`, `btc_gold_monitor`, `event_trades`, `gold_straddle_trades`

---

## What Codex needs to build

### Priority 1: Funding Survival Backtester
**File:** `backtester/funding_survival.py` (skeleton exists)

The critical question: **does headline APR survive 30 days in practice?**

```python
# The test:
# For every period where funding > 40%/yr, simulate entry
# Track: actual income collected, rate decay, flip events, stop-outs
# Compare: realised APR vs headline APR at entry
# Output: survival rate, avg realised income, P25/P75 distribution
```

We have 166 days of real data. The backtester skeleton is in `backtester/funding_survival.py`. 
Needs: `load_funding_history()` connected to the live DB, then full simulation loop.

### Priority 2: Persistence Score Model
**File:** `signal_engine/persistence.py` (needs creating)

Binary classifier: given a coin's historical rate profile, predict "will it stay positive for 30 days?"

Features available:
- Rate volatility (std of 8h rates)
- Rate trend (slope over last 30 days)
- Consecutive positive periods count
- Coin category (crypto vs stock perp vs commodity)
- OI change rate
- Long/short ratio

Labels: 1 if rate stayed positive for next 30 days, 0 if it flipped

Training data: ~15 coins × 166 days / 8h = ~7,500 labelled examples (small but real)

### Priority 3: Event Volatility Model
**File:** `signal_engine/event_breakout.py` (needs creating)

No prediction of direction. Only: "does the market make a large enough move post-event to be worth trading?"

```
Input:  pre-event range (last 2h high-low)
        event type (CPI, NFP, FOMC)
        actual vs forecast deviation (%)
Output: P(move > 50pts) in next 30 min
```

Training data: 18 months of CPI/NFP events (in HANDOVER below)

### Priority 4: BTC/Gold Regime Classifier
**File:** `signal_engine/regime.py` (needs creating)

Multi-factor regime detection (0-10 score):
- BTC/Gold ratio Z-score vs 6m, 12m average
- BTC perpetual funding rate
- VIX level and trend
- DXY level and trend
- 10Y real yield
- BTC 30-day momentum vs Gold 30-day momentum

Already running live (see `btc_gold_monitor.py`). Needs ML layer to improve signal quality.

---

## Architecture decisions already made

| Decision | Choice | Reason |
|---|---|---|
| Database | SQLite | Simple, no infrastructure, portable |
| Exchange data | Binance public API | Most liquid perps, no auth needed |
| Execution layer | IG Group API | UK FCA regulated, spread betting tax-free |
| Hedge instrument | QQQ/SPY via IG spread bet | Accessible, liquid, tax-free |
| Research approach | Paper-first | Validate edge before real capital |

## UK Legal Constraint

**Binance crypto/stock perps are FCA-restricted for UK retail clients.**

All current positions are paper-only. Legal routes being evaluated:
- **Hyperliquid** (decentralised, no KYC, limited instrument selection)
- **dYdX v4** (decentralised, ~39% APR on ENA-USD right now)
- **IBKR** for stock hedge leg (FCA regulated, low cost)

## Capital and timeline

- **Current capital:** £2,000 (paper trading)
- **Day 11 of 30** — paper trading ends 10 June 2026
- **Decision point:** if results are consistent → go live with real money
- **Target:** validate 30%+ APR survival rate before committing capital

## Questions for Codex

1. What feature engineering improves persistence prediction the most?
2. Is 7,500 training examples enough for a reliable classifier?
3. Should we use a simple logistic regression or gradient boosting given data size?
4. How do we handle the regime-switching nature of funding rates (HMM vs threshold models)?
5. For the event model — is 18 months of CPI/NFP data (24 events) enough to train on?

---

## First PR suggestion

```
feat: funding survival backtest

- Complete backtester/funding_survival.py
- Connect to live 166-day SQLite database
- Run backtest for top 10 coins
- Output: survival rate, realised vs headline APR, P25/P75
- Add tests/test_backtester.py with synthetic data
```

## Shared data export

To get the full 42,000-row funding history CSV for analysis:
```bash
ssh root@72.62.212.97
cd /root/.openclaw/workspace/projects/trading-bot
python3 -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('trading_data.db')
df = pd.read_sql('SELECT * FROM funding_history', conn)
df.to_csv('/tmp/funding_history_166d.csv', index=False)
print(df.shape)
"
```

Then `scp root@72.62.212.97:/tmp/funding_history_166d.csv .`

---

*Claude has access to the live VPS and can run code, pull data, and test models at any time.  
Codex handles model architecture and training. Both commit to this repo.*
