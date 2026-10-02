# kalshi-commodity-agent

Read-only cushion caller for Kalshi's **Gold 15-minute (`KXGOLD15M`)** and **WTI 15-minute (`KXWTI15M`)**
markets: the same method as [`kalshi-btc-agent`](../kalshi-btc-agent), one codebase for both commodities.
It never places an order.

```
agent.py [gold|wti]      card for the open window (no alert)
agent.py --run           scheduled: log every minute, settle calls, alert once per window (alerts OFF by default)
agent.py --scorecard     live record by asset and by minute of the first call
backtest.py              calibrate the gate per asset against every settled Kalshi window (writes gate-<asset>.json)
archive.py               keep the live proxy's 1-minute history (Hyperliquid only serves ~3.5 days)
recal.sh                 weekly (Sun 06:20): archive + backtest + scorecard, commit and push
```

## How it differs from the BTC agent

| | BTC | Gold / WTI |
|---|---|---|
| Settles on | average of the last 60 s of BRTI | ONE Pyth 1-minute candle close (window close vs window open) |
| Settlement price source | paid (CF Benchmarks), proxied from Coinbase + Bitstamp | Pyth; its API now needs a key, so proxied by Hyperliquid's real-time `xyz:GOLD` / `xyz:CL` perps (keyless, 24/7) |
| Gap | spot − strike | proxy now − proxy at the window open (the strike *is* Pyth at the open, so the level basis between proxy and Pyth cancels) |
| Time left | minutes left − ⅔ (averaging) | minutes left (point settlement) |
| Volatility | realized, Chronos-2 as challenger | realized only |
| Backtest price path | Coinbase/Bitstamp 1m, 3 weeks | Yahoo CME futures 1m, last 7 days (10 min delayed, so history only) |

Measured proxy quality (Pyth 15-minute window change vs proxy change): WTI corr 0.997, error 7% of the move;
gold corr 0.975, error 22% of the move (CME gold futures: 0.997, but they are 10 minutes delayed live).
`sigma_proxy` in `gate-<asset>.json` is that error and enters every call as extra variance.

## Honest status

* Pre-registered gate rule (copied from the BTC agent): lowest confidence whose fit-half hit rate has a Wilson lower bound >= 90%, reported on the held-out half.
* Minute-by-minute cells are hypotheses for the live scorecard, not findings. Not proven until 10+ separate days of live calls.
* The backtest sample is about one week of 1-minute prices, so the gate is provisional; `archive.py` and the weekly recalibration sharpen it.
* The BTC lesson applies: a call can be accurate and still priced in. Check "Edge vs ask" before treating a call as a trade idea.

## Layout

```
assets.json            per-asset series, proxies, defaults
gate-<asset>.json      calibrated gate + hit-rate table (rewritten weekly)
config.json            alerts per asset (off), optional min_conf_override
data/windows-*.jsonl   every settled Kalshi window ever seen (Kalshi's API does not keep them forever)
data/bars/*.csv.gz     archived Hyperliquid 1m bars
data/evals-*.jsonl     every minute's evaluation + settled calls (hourly autocommit)
results/               backtest reports + scorecard snapshots
```
