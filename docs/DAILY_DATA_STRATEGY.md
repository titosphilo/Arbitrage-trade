# Daily Tradable Data Strategy

The goal is to find more daily opportunities without forcing a trade every day.

A daily scanner should produce:

```text
TRADE / WATCH / SKIP
```

The safest daily system is one that is allowed to say `SKIP` often.

## Daily data to collect

| Data | Why it matters | Frequency |
|---|---|---|
| Overnight return | Shows whether London/Asia created momentum | Morning |
| Intraday range expansion | Confirms whether today has enough movement | Intraday |
| Realized volatility | Controls stop size and whether to reduce risk | Intraday |
| VIX change | Measures equity fear/relief | Daily/intraday |
| DXY change | Measures dollar pressure | Daily/intraday |
| Yield change | Measures rate pressure | Daily/intraday |
| Funding APR | Finds carry opportunities | Every funding interval |
| P(sticky) | Filters fragile funding spikes | Daily |
| News sentiment | Captures qualitative psychology | Morning/intraday |
| Positioning/crowding | Finds squeeze or fade conditions | Daily |
| Price confirmation | Prevents narrative-only trades | Intraday |
| Liquidity score | Blocks thin products | Daily |

## Daily setup types

### 1. Momentum continuation

Trade only when daily movement has confirmation.

Example:

```text
US500 gaps up + VIX falling + price confirms -> possible long
```

### 2. Funding carry

Trade when carry is high and persistent.

Example:

```text
Funding APR > 40% + P(sticky) > 70% -> possible short perp
```

### 3. Mean reversion / crowd fade

Trade only when crowding is extreme and price confirms the reversal.

Example:

```text
Everyone is long + bullish news fails + price turns down -> possible fade
```

## Qualitative psychology layer

Ask each morning:

1. What is the market worried about today?
2. What outcome would create fear?
3. What outcome would create relief?
4. Is the market already positioned for that outcome?
5. Did price confirm the emotional reaction?

Then encode that as structured inputs, not free-form opinion.

## Safety rule

Daily data can create more candidates, but it must not change the pilot guard:

- GBP 5 max risk per trade
- GBP 10 daily stop
- one open position
- no leverage
- protective stop required
- manual confirmation required

## Practical morning workflow

1. Scan macro calendar: major event or quiet day?
2. Read VIX, DXY and yields: fear, dollar, rates.
3. Check overnight move in US500, GBPUSD, EURUSD, BTC and gold.
4. Check funding opportunities and P(sticky).
5. Score all instruments with `signal_engine.daily_opportunities`.
6. Only consider `TRADE` if price confirms intraday.
7. Send the final proposal through `risk_engine.live_guard`.

## Important note

A daily scanner should increase *preparedness*, not trade frequency at any cost. The edge is in waiting for clear alignment.
