# Gold 15-minute backtest — 2026-10-04 06:20

Series KXGOLD15M, settles on Pyth 1OZGOLD/USD, 1-minute candle close.
458 settled windows with a CME price path (2026-09-27T23:15:00Z → 2026-10-02T21:00:00Z); 30 new windows added to the permanent archive (data/windows-gold.jsonl, 4446 on Kalshi now).

## 1. Proxy error against Pyth (change over a 15-minute window)

| proxy | windows | RMS error $ | role |
|---|---|---|---|
| Hyperliquid xyz:GOLD | 186 | 1.054 | LIVE proxy; this is sigma_proxy in the model |
| Yahoo CME GC=F | 433 | 0.534 | backtest price path only (delayed live) |

## 2. Calibration (Brier, lower is better; all checkpoints)

| source | fit half | test half |
|---|---|---|
| gap / realized vol | 0.1476 | 0.1559 |
| Kalshi mid at the same minute | 0.1470 | 0.1544 |

## 3. Gate sweep

Call = the side the model favours, only when its confidence clears the bar. `paid` = Kalshi ask for that side at that minute. `EV/contract` = win − paid − fee; positive means the call beat the market.

| min conf | fit n | fit hit [95% CI] | test n | test hit [95% CI] | test avg conf | test avg paid | test EV/contract |
|---|---|---|---|---|---|---|---|
| 0.80 | 508 | 94.9% [93%–96%] | 479 | 95.0% [93%–97%] | 92.2% | 0.93 | +0.012 |
| 0.85 | 400 | 97.0% [95%–98%] | 382 | 96.3% [94%–98%] | 94.6% | 0.94 | +0.008 |
| 0.90 | 305 | 97.7% [95%–99%] | 302 | 98.0% [96%–99%] | 96.5% | 0.96 | +0.012 |
| 0.93 | 250 | 97.6% [95%–99%] | 239 | 98.3% [96%–99%] | 97.8% | 0.97 | +0.007 |
| 0.95 | 212 | 97.6% [95%–99%] | 199 | 99.5% [97%–100%] | 98.6% | 0.97 | +0.014 |
| 0.97 | 151 | 99.3% [96%–100%] | 163 | 100.0% [98%–100%] | 99.2% | 0.98 | +0.013 |
| 0.98 | 119 | 99.2% [95%–100%] | 137 | 100.0% [97%–100%] | 99.5% | 0.98 | +0.010 |
| 0.99 | 89 | 100.0% [96%–100%] | 111 | 100.0% [97%–100%] | 99.7% | 0.98 | +0.009 |

## 4. At the chosen gate (0.80), by minute into the window (test half)

EV 95% CI is a bootstrap over calls (calls cluster in time, so it is too narrow); cells were not pre-registered.

| minute | calls | hit | avg ask paid | EV/contract [95% CI] | median cushion $ |
|---|---|---|---|---|---|
| 3 | 18 | 88.9% | 0.86 | +0.021 [-0.148, +0.141] | 4.50 |
| 5 | 45 | 95.6% | 0.88 | +0.065 [-0.006, +0.117] | 4.50 |
| 7 | 70 | 94.3% | 0.89 | +0.043 [-0.016, +0.089] | 4.70 |
| 9 | 93 | 93.5% | 0.91 | +0.012 [-0.042, +0.056] | 4.60 |
| 11 | 113 | 94.7% | 0.94 | -0.005 [-0.043, +0.029] | 4.60 |
| 13 | 140 | 97.1% | 0.97 | -0.008 [-0.037, +0.016] | 4.00 |

## gate-gold.json

```json
{
  "asset": "gold",
  "series": "KXGOLD15M",
  "sigma_proxy": 1.0536,
  "min_conf": 0.8,
  "min_z": 0.84,
  "min_minute": 3,
  "hit_table": [
    {
      "conf_from": 0.5,
      "conf_to": 0.6,
      "n": 583,
      "hit": 0.5523,
      "ci": [
        0.512,
        0.592
      ]
    },
    {
      "conf_from": 0.6,
      "conf_to": 0.7,
      "n": 565,
      "hit": 0.6673,
      "ci": [
        0.627,
        0.705
      ]
    },
    {
      "conf_from": 0.7,
      "conf_to": 0.8,
      "n": 445,
      "hit": 0.7865,
      "ci": [
        0.746,
        0.822
      ]
    },
    {
      "conf_from": 0.8,
      "conf_to": 0.85,
      "n": 205,
      "hit": 0.8829,
      "ci": [
        0.832,
        0.92
      ]
    },
    {
      "conf_from": 0.85,
      "conf_to": 0.9,
      "n": 175,
      "hit": 0.9257,
      "ci": [
        0.877,
        0.956
      ]
    },
    {
      "conf_from": 0.9,
      "conf_to": 0.95,
      "n": 196,
      "hit": 0.9643,
      "ci": [
        0.928,
        0.983
      ]
    },
    {
      "conf_from": 0.95,
      "conf_to": 0.98,
      "n": 155,
      "hit": 0.9677,
      "ci": [
        0.927,
        0.986
      ]
    },
    {
      "conf_from": 0.98,
      "conf_to": 1.0,
      "n": 256,
      "hit": 0.9961,
      "ci": [
        0.978,
        0.999
      ]
    }
  ],
  "calibrated_on": "433 windows, 2026-09-27T23:15:00Z \u2192 2026-10-02T21:00:00Z",
  "calibrated_at": "2026-10-04T10:20:14Z"
}
```
