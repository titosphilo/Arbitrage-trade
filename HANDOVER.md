# Handover - Funding Arb Research + Trading Pilot
**Updated:** 7 June 2026
**Repo:** https://github.com/titosphilo/Arbitrage-trade

## Security Notice

Live account credentials must never be committed to this repository. Credentials previously present in this file must be treated as compromised and rotated immediately. Store replacements only in environment variables or the VPS secret manager.

Required environment variables are documented in `.env.example`. Never commit real values.

## Trading Status

- Funding positions remain paper-only.
- Live event trading must stay paused until the live execution code is committed and audited.
- Any £500 pilot must use manual confirmation, minimum position size, no leverage, hard stops, stale-data blocking, duplicate-order protection, and a daily kill switch.

## Research Findings

1. Sticky funding coins exist, but headline APR decays materially.
2. Persistence classification is useful for filtering fragile funding spikes.
3. High-APR names can have poor 30-day survival.
4. Event-trading evidence is still too small for unattended execution.
5. Full trade P&L must include spreads, slippage, gaps, fees and rejected exits.

## Current Research Modules

- `backtester/funding_survival.py`
- `signal_engine/persistence.py`
- `signal_engine/rank.py`
- `signal_engine/position_sizer.py`
- `risk_engine/safety_engine.py`

## Required Before Live Automation

1. Rotate all credentials exposed in Git history.
2. Purge secrets from repository history.
3. Add the exact VPS execution code to a private repository.
4. Connect pre-trade safety checks directly to every order path.
5. Add idempotency, stale-data rejection, hard stops and an account-level kill switch.
6. Complete walk-forward validation and a sufficiently large paper-trade sample.
7. Start at minimum size with manual confirmation and no leverage.

## UK Note

Use only products and venues legally available to the account holder. Obtain professional advice where needed. Do not rely on repository notes as legal or tax advice.
