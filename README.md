# Funding Arbitrage Research Engine

> Research-first trading model. Discover which edges survive fees, slippage, funding decay, and risk before committing capital.

## Philosophy

**No live trading until the model proves itself.** This repo is a research engine that:
1. Scans for funding arbitrage opportunities across perps
2. Scores them by persistence, liquidity, and risk
3. Backtests survival after realistic costs
4. Runs a live paper portfolio

When paper results are consistent over 30+ days, manual-confirm execution is added.

## Architecture

```
arb-research/
├── data_ingestion/     # Funding rates, prices, OI, basis
├── signal_engine/      # APR rank, persistence, crowding, flip risk
├── risk_engine/        # Position sizing, liquidation, drawdown, correlation
├── backtester/         # Funding income, MTM PnL, fees, stop rules
├── dashboard/          # Opportunities, income estimate, risk flags
└── research/           # Jupyter notebooks, analysis, findings
```

## Research Tracks

### Track 1: Funding Basket Model
Short high-positive-funding perps, rotate daily/every interval.
Test whether headline APR survives volatility and adverse price moves.

### Track 2: Hedged Stock-Perp Model
Short stock perp (COINUSDT, AMZNUSDT, METAUSDT), hedge with stock/Nasdaq proxy.
Estimate basis/funding income net of hedge error.

### Track 3: Event Volatility Model
Gold/Nasdaq/BTC around CPI and NFP.
No prediction — only post-event range expansion entry.

## Milestone 1 (current)
- [x] Data ingestion (Binance perp funding rates, prices)
- [x] Signal engine (APR rank, persistence score)
- [x] Risk engine (position sizing, concentration)
- [x] Paper portfolio tracker
- [ ] Backtester (30-day funding survival test)
- [ ] Dashboard (opportunity scanner)

## Installation

```bash
pip install -r requirements.txt
python -m data_ingestion.scanner      # scan current rates
python -m signal_engine.rank          # rank by edge score
python -m backtester.run              # backtest last 30 days
```

## Key Findings (live data)

| Perp | Gross APR | After 50% haircut | Hedge | Status |
|------|-----------|-------------------|-------|--------|
| COINUSDT | ~140% | ~70% | Long COIN/BKCH | ENTER |
| AMZNUSDT | ~130% | ~65% | Long AMZN/QQQ | ENTER |
| METAUSDT | ~80% | ~40% | Long META/QQQ | ENTER |

*Haircut accounts for: rate decay, spread costs, hedge error, liquidation buffer*

## UK Note
Binance crypto/stock perps are FCA-restricted for UK retail. 
Legal routes: Hyperliquid, dYdX (fewer instruments, similar logic).
All positions are paper-only until a compliant exchange is used.

## Collaborators
- Research & architecture: Claude (Anthropic) + Codex (OpenAI)
- Live data: Binance public API, Yahoo Finance
- Historical data: 166-day funding rate DB (100 coins)
