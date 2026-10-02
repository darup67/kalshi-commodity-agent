# Gold 15-minute backtest — 2026-10-02 09:47

Series KXGOLD15M, settles on Pyth 1OZGOLD/USD, 1-minute candle close.
496 settled windows with a CME price path (2026-09-25T05:15:00Z → 2026-10-02T13:30:00Z); 4411 new windows added to the permanent archive (data/windows-gold.jsonl, 4416 on Kalshi now).

## 1. Proxy error against Pyth (change over a 15-minute window)

| proxy | windows | RMS error $ | role |
|---|---|---|---|
| Hyperliquid xyz:GOLD | 331 | 1.080 | LIVE proxy; this is sigma_proxy in the model |
| Yahoo CME GC=F | 470 | 0.444 | backtest price path only (delayed live) |

## 2. Calibration (Brier, lower is better; all checkpoints)

| source | fit half | test half |
|---|---|---|
| gap / realized vol | 0.1483 | 0.1492 |
| Kalshi mid at the same minute | 0.1461 | 0.1471 |

## 3. Gate sweep

Call = the side the model favours, only when its confidence clears the bar. `paid` = Kalshi ask for that side at that minute. `EV/contract` = win − paid − fee; positive means the call beat the market.

| min conf | fit n | fit hit [95% CI] | test n | test hit [95% CI] | test avg conf | test avg paid | test EV/contract |
|---|---|---|---|---|---|---|---|
| 0.80 | 538 | 94.8% [93%–96%] | 543 | 95.2% [93%–97%] | 91.9% | 0.93 | +0.015 |
| 0.85 | 429 | 96.7% [95%–98%] | 431 | 97.0% [95%–98%] | 94.4% | 0.94 | +0.015 |
| 0.90 | 323 | 97.5% [95%–99%] | 335 | 98.5% [97%–99%] | 96.4% | 0.96 | +0.016 |
| 0.93 | 265 | 97.7% [95%–99%] | 259 | 98.8% [97%–100%] | 97.8% | 0.97 | +0.012 |
| 0.95 | 224 | 98.2% [95%–99%] | 214 | 99.1% [97%–100%] | 98.6% | 0.97 | +0.009 |
| 0.97 | 163 | 99.4% [97%–100%] | 174 | 100.0% [98%–100%] | 99.2% | 0.98 | +0.013 |
| 0.98 | 126 | 99.2% [96%–100%] | 147 | 100.0% [97%–100%] | 99.5% | 0.98 | +0.009 |
| 0.99 | 98 | 100.0% [96%–100%] | 112 | 100.0% [97%–100%] | 99.8% | 0.98 | +0.007 |

## 4. At the chosen gate (0.80), by minute into the window (test half)

EV 95% CI is a bootstrap over calls (calls cluster in time, so it is too narrow); cells were not pre-registered.

| minute | calls | hit | avg ask paid | EV/contract [95% CI] | median cushion $ |
|---|---|---|---|---|---|
| 3 | 27 | 85.2% | 0.85 | -0.011 [-0.158, +0.106] | 4.20 |
| 5 | 48 | 93.8% | 0.88 | +0.046 [-0.031, +0.104] | 4.25 |
| 7 | 81 | 95.1% | 0.89 | +0.046 [-0.006, +0.088] | 4.40 |
| 9 | 109 | 94.5% | 0.91 | +0.022 [-0.024, +0.059] | 4.30 |
| 11 | 128 | 96.1% | 0.94 | +0.006 [-0.026, +0.033] | 4.35 |
| 13 | 150 | 97.3% | 0.97 | -0.005 [-0.034, +0.016] | 3.90 |

## gate-gold.json

```json
{
  "asset": "gold",
  "series": "KXGOLD15M",
  "sigma_proxy": 1.0795,
  "min_conf": 0.8,
  "min_z": 0.84,
  "min_minute": 3,
  "hit_table": [
    {
      "conf_from": 0.5,
      "conf_to": 0.6,
      "n": 625,
      "hit": 0.56,
      "ci": [
        0.521,
        0.598
      ]
    },
    {
      "conf_from": 0.6,
      "conf_to": 0.7,
      "n": 593,
      "hit": 0.6847,
      "ci": [
        0.646,
        0.721
      ]
    },
    {
      "conf_from": 0.7,
      "conf_to": 0.8,
      "n": 485,
      "hit": 0.7918,
      "ci": [
        0.753,
        0.826
      ]
    },
    {
      "conf_from": 0.8,
      "conf_to": 0.85,
      "n": 221,
      "hit": 0.8778,
      "ci": [
        0.828,
        0.915
      ]
    },
    {
      "conf_from": 0.85,
      "conf_to": 0.9,
      "n": 202,
      "hit": 0.9307,
      "ci": [
        0.887,
        0.958
      ]
    },
    {
      "conf_from": 0.9,
      "conf_to": 0.95,
      "n": 220,
      "hit": 0.9682,
      "ci": [
        0.936,
        0.985
      ]
    },
    {
      "conf_from": 0.95,
      "conf_to": 0.98,
      "n": 165,
      "hit": 0.9697,
      "ci": [
        0.931,
        0.987
      ]
    },
    {
      "conf_from": 0.98,
      "conf_to": 1.0,
      "n": 273,
      "hit": 0.9963,
      "ci": [
        0.98,
        0.999
      ]
    }
  ],
  "calibrated_on": "467 windows, 2026-09-25T05:15:00Z \u2192 2026-10-02T13:30:00Z",
  "calibrated_at": "2026-10-02T13:47:01Z"
}
```
