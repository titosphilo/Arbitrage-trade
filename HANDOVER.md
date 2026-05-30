# Handover — Funding Arb Research + Live Trading
**Date:** 28 May 2026 | **Day:** 19/30 | **VPS:** 72.62.212.97
**Repo:** https://github.com/titosphilo/Arbitrage-trade

---

## LIVE TRADING

### IG Account (LIVE £500)
- Account: JWEGH (Spread bet, tax-free)
- API Key: 93c7393014e4cdd2b345eba0479b8431bb8761af
- User: JACQPH72304769 / 1506Boudha!
- Base: https://api.ig.com/gateway/deal
- File: /root/.openclaw/workspace/projects/trading-bot/event_trader.py

### Instruments + Sizes
| Instrument | Epic | Size | Events |
|---|---|---|---|
| US 500 | IX.D.SPTRD.DAILY.IP | £1/pt | NFP, CPI, FOMC, ADP, GDP, PCE, ISM, Claims |
| GBP/USD | CS.D.GBPUSD.TODAY.IP | £0.50/pip | BOE, UK CPI, UK Jobs |
| EUR/USD | CS.D.EURUSD.TODAY.IP | £0.50/pip | ECB, German CPI |

### Safety scaling
- £400+ → £1.00/pt | £250+ → £0.50/pt | £150+ → £0.25/pt | <£150 → PAUSE

### Signal logic
- HOT (actual > forecast >5%): SELL equities / BUY USD pairs
- COOL (actual < forecast >5%): BUY equities / SELL USD pairs
- IN-LINE: skip | BORDERLINE (5-10%): half size

### Next events
- Thu 29 May 12:30 UTC — Jobless Claims → US 500
- Fri 6 Jun 12:30 UTC — NFP → US 500 (biggest)
- Wed 11 Jun — UK CPI → GBP/USD
- Thu 12 Jun — ECB → EUR/USD

### Calendar fix (important)
ForexFactory requires: `Referer: https://www.forexfactory.com/` header
Without it → 429 rate limit → missed trade (happened today with GDP)
Fixed in current event_trader.py with 3x retry logic

---

## DATABASE
Path: /root/.openclaw/workspace/projects/trading-bot/trading_data.db

| Table | Rows | Notes |
|---|---|---|
| btc_price_1m | 22,557 | 19 days BTC 1-min |
| gold_price_1m | 53,870 | Gold 1-min |
| funding_history | 59,204 | 8h rates, 258 coins |
| coin_profiles | 258 | sticky_score, category |
| macro_snapshot | 1,916 | VIX/DXY/yields every 5min |
| ai_oracle_log | 124 | 5-model readings every 4h |
| event_trades | 0 | Live trades (first pending NFP 6 Jun) |
| funding_positions | 13 | Open paper positions |

---

## KEY FINDINGS

1. **Sticky coins confirmed** — 15 coins 100% positive over 166 days
2. **Classifier accuracy 91.6%** on 215 symbols
3. **Realised APR = 75% of headline** (backtest validated on 46k rows)
4. **No coins pass all 4 quality filters today** — all at 5.5%/yr floor (normal)
5. **COINUSDT 141%/yr → 10.8% survival** — classifier correctly rejects
6. **Margin confirmed** — US 500 £1/pt = £376 margin (5% of notional)
7. **GDP lesson** — second estimates don't move markets; first-release events matter

---

## WHAT CODEX NEEDS TO BUILD

### 1. Funding Momentum Detector (signal_engine/momentum.py)
Detect coins *becoming* sticky before they fully qualify
- Enter when: APR rising + streak growing + OI rising + vol stable
- Catches sticky trades 3-5 periods earlier

### 2. Re-entry System (signal_engine/reentry.py)
If coin was sticky before AND APR recovers >40% AND streak resumes → re-enter faster

### 3. Capital Rotation (signal_engine/rotation.py)
Rank every 8h by: expected_income × P(sticky) / volatility
Move capital from weak to stronger positions

### 4. Event ML Model (signal_engine/event_model.py)
Train on 18 months CPI/NFP — features: deviation%, event type, VIX, pre-event drift
Output: P(move >50pts in 30min)

---

## GITHUB COLLABORATION

**Codex built:** Signal dataclass, compute_edge_score(), persistence classifier,
funding_survival backtester, src/models.py, src/risk.py, test suite

**Claude built:** All VPS infrastructure, live trading, quality_filter.py,
position_sizer.py, decay_exit.py, decay_predictor.py, spot_perp_basis.py,
src/cli.py, 46k-row data export, 215-symbol features dataset

---

## QUESTIONS FOR CODEX

1. With 215 symbols / 91.6% accuracy — how many more points to reach 95%?
2. Can momentum detection use existing features or needs OI time-series?
3. 24 CPI/NFP events — enough for event ML or need transfer learning?
4. Capital rotation: Sharpe-ranking or RL?

---

## UK LEGAL NOTE
Binance crypto/stock perps FCA-restricted for UK retail.
All funding positions paper-only.
Legal routes: Hyperliquid, dYdX v4, IBKR for hedge leg.
