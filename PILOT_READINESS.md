# GBP 500 Controlled Pilot

This is a capital-preservation test, not a profit target. Live automation remains disabled until every launch gate below is satisfied.

## Non-negotiable limits

| Control | Limit |
|---|---:|
| Starting equity | GBP 500 |
| Planned risk per trade | GBP 5 maximum |
| Daily loss stop | GBP 10 |
| Weekly loss stop | GBP 20 |
| Concurrent positions | 1 |
| Leverage | 1.0x maximum |
| Manual confirmation | Required for every order |
| Protective stop | Required before submission |
| Stale market data | Block after 5 seconds |
| Stale signal | Block after 15 seconds |
| Stale event calendar | Block after 15 minutes |

## Immediate security gate

- Rotate the IG password and API key that were exposed in Git history.
- Invalidate all active broker sessions.
- Purge the exposed secret from repository history.
- Store replacement credentials only in environment variables or a VPS secret manager.
- Confirm withdrawal and account-management capabilities are not available to the trading process.

## Execution gate

The exact VPS broker adapter must be committed to a private repository and reviewed. It must:

1. Call `risk_engine.live_guard.evaluate_trade()` immediately before every order.
2. Refuse orders whenever `allowed` is false.
3. Use a unique persistent `broker_order_key` for idempotency.
4. Persist the key before submission and reconcile it with broker confirmations after submission.
5. Attach a broker-side protective stop in the same request, or abort the order.
6. Reject signals if price, signal, or calendar data is stale.
7. Activate the account kill switch after the daily or weekly loss limit.
8. Reconcile open positions directly from the broker before sizing a new order.
9. Log request, response, confirmation, fill, stop, close and realized P&L.
10. Never retry an order blindly after a timeout; query by idempotency key first.

## Validation gate

Before the first live order:

- All automated tests pass.
- At least 20 consecutive demo proposals pass through the same execution path.
- Duplicate, timeout, rejected-order and stale-data scenarios are tested.
- The broker reports the expected account, currency and available funds.
- Position size and stop risk are independently recalculated from the broker quote.
- The first live order uses the broker minimum size and risks no more than GBP 5.

## Pilot progression

1. First 5 live trades: minimum size, one position, manual confirmation.
2. Stop the pilot after any system error, duplicate order, missing stop or unexplained P&L.
3. Do not increase size based on a winning streak.
4. Review after at least 20 live trades and four weeks, whichever is later.
5. Increase risk only if realized P&L, slippage and drawdown match the tested assumptions.

## Current decision

**Not ready for a live order yet.** The repository does not contain the VPS broker execution adapter, exposed credentials still require rotation/history purge, and the event strategy lacks a sufficient live sample.
