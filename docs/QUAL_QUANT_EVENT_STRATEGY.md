# Qualitative + Quantitative Event Strategy

This layer is designed to create more valid trade opportunities without weakening risk controls.

## Core idea

Markets move after events because the data changes expectations and expectations change emotion.

The model scores both:

- **Quantitative surprise:** actual vs forecast
- **Qualitative psychology:** how traders are likely to feel and react

A trade is only considered when both agree.

## Inputs

| Input | Meaning |
|---|---|
| `actual` / `forecast` | Objective event surprise |
| `consensus_bias` | What the market seemed to expect before the event |
| `positioning_crowding` | Whether traders were already leaning one way |
| `narrative_strength` | How strongly the event fits the current market story |
| `event_credibility` | Whether this event is a first-tier market mover |
| `pre_event_drift` | Whether the market already moved before release |
| `post_event_confirmation` | Whether price confirms after release |
| `volatility_regime` | Whether stop risk is elevated |

## Example psychology

Hot CPI can create fear:

```text
higher inflation -> higher rates fear -> equities down -> USD stronger
```

Cool CPI can create relief:

```text
lower inflation -> rate-cut hope -> equities up -> USD weaker
```

Strong NFP can be risk-on if growth matters most, but risk-off if the market is mainly worried about rates. That is why `narrative_strength`, `consensus_bias`, and confirmation matter.

## Trade permissions

| Permission | Meaning |
|---|---|
| `TRADE` | Surprise, narrative, crowding, and confirmation align |
| `WATCH` | Idea is plausible but confirmation/conviction is not enough |
| `SKIP` | No clear emotional edge |

## Risk rule

This module does **not** place trades and does **not** override the pilot guard.

Every trade must still pass:

- GBP 5 max risk per trade
- GBP 10 daily loss stop
- one open position
- no leverage
- protective stop required
- manual confirmation required

## How it increases trade count safely

Instead of only trading CPI/NFP with fixed rules, we can include more events when the psychology is clear:

- jobless claims
- retail sales
- ISM
- PCE
- central-bank decisions
- press-conference surprises
- first GDP releases

But each event needs the same structure: expectation, surprise, psychological narrative, and price confirmation.
