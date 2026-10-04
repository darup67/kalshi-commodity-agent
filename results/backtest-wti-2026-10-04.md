# WTI oil 15-minute backtest — 2026-10-04 06:20

Series KXWTI15M, settles on Pyth PYTHOIL/USD, 1-minute candle close.
491 settled windows with a CME price path (2026-09-27T23:15:00Z → 2026-10-03T04:00:00Z); 57 new windows added to the permanent archive (data/windows-wti.jsonl, 4471 on Kalshi now).

## 1. Proxy error against Pyth (change over a 15-minute window)

| proxy | windows | RMS error $ | role |
|---|---|---|---|
| Hyperliquid xyz:CL | 214 | 0.019 | LIVE proxy; this is sigma_proxy in the model |
| Yahoo CME CL=F | 429 | 0.022 | backtest price path only (delayed live) |

## 2. Calibration (Brier, lower is better; all checkpoints)

| source | fit half | test half |
|---|---|---|
| gap / realized vol | 0.1471 | 0.1731 |
| Kalshi mid at the same minute | 0.1439 | 0.1724 |

## 3. Gate sweep

Call = the side the model favours, only when its confidence clears the bar. `paid` = Kalshi ask for that side at that minute. `EV/contract` = win − paid − fee; positive means the call beat the market.

| min conf | fit n | fit hit [95% CI] | test n | test hit [95% CI] | test avg conf | test avg paid | test EV/contract |
|---|---|---|---|---|---|---|---|
| 0.80 | 494 | 95.7% [94%–97%] | 479 | 92.1% [89%–94%] | 92.6% | 0.92 | -0.014 |
| 0.85 | 409 | 96.1% [94%–98%] | 383 | 95.6% [93%–97%] | 95.1% | 0.95 | +0.000 |
| 0.90 | 331 | 97.0% [95%–98%] | 311 | 96.5% [94%–98%] | 96.8% | 0.96 | -0.001 |
| 0.93 | 279 | 98.2% [96%–99%] | 258 | 98.4% [96%–99%] | 97.9% | 0.97 | +0.009 |
| 0.95 | 242 | 98.8% [96%–100%] | 221 | 99.1% [97%–100%] | 98.5% | 0.97 | +0.011 |
| 0.97 | 195 | 99.5% [97%–100%] | 167 | 98.8% [96%–100%] | 99.4% | 0.98 | -0.001 |
| 0.98 | 178 | 99.4% [97%–100%] | 150 | 99.3% [96%–100%] | 99.6% | 0.98 | +0.001 |
| 0.99 | 150 | 100.0% [98%–100%] | 120 | 99.2% [95%–100%] | 99.8% | 0.99 | -0.004 |

## 4. At the chosen gate (0.80), by minute into the window (test half)

EV 95% CI is a bootstrap over calls (calls cluster in time, so it is too narrow); cells were not pre-registered.

| minute | calls | hit | avg ask paid | EV/contract [95% CI] | median cushion $ |
|---|---|---|---|---|---|
| 3 | 27 | 81.5% | 0.86 | -0.059 [-0.209, +0.065] | 0.28 |
| 5 | 43 | 83.7% | 0.87 | -0.042 [-0.158, +0.053] | 0.25 |
| 7 | 68 | 91.2% | 0.89 | +0.006 [-0.060, +0.066] | 0.24 |
| 9 | 89 | 91.0% | 0.92 | -0.023 [-0.082, +0.032] | 0.24 |
| 11 | 117 | 93.2% | 0.94 | -0.016 [-0.065, +0.026] | 0.23 |
| 13 | 135 | 97.0% | 0.96 | -0.000 [-0.024, +0.022] | 0.20 |

## gate-wti.json

```json
{
  "asset": "wti",
  "series": "KXWTI15M",
  "sigma_proxy": 0.0189,
  "min_conf": 0.8,
  "min_z": 0.84,
  "min_minute": 3,
  "hit_table": [
    {
      "conf_from": 0.5,
      "conf_to": 0.6,
      "n": 656,
      "hit": 0.5671,
      "ci": [
        0.529,
        0.604
      ]
    },
    {
      "conf_from": 0.6,
      "conf_to": 0.7,
      "n": 516,
      "hit": 0.6085,
      "ci": [
        0.566,
        0.65
      ]
    },
    {
      "conf_from": 0.7,
      "conf_to": 0.8,
      "n": 419,
      "hit": 0.7733,
      "ci": [
        0.731,
        0.811
      ]
    },
    {
      "conf_from": 0.8,
      "conf_to": 0.85,
      "n": 181,
      "hit": 0.8564,
      "ci": [
        0.798,
        0.9
      ]
    },
    {
      "conf_from": 0.85,
      "conf_to": 0.9,
      "n": 150,
      "hit": 0.92,
      "ci": [
        0.865,
        0.954
      ]
    },
    {
      "conf_from": 0.9,
      "conf_to": 0.95,
      "n": 179,
      "hit": 0.9106,
      "ci": [
        0.86,
        0.944
      ]
    },
    {
      "conf_from": 0.95,
      "conf_to": 0.98,
      "n": 135,
      "hit": 0.9778,
      "ci": [
        0.937,
        0.992
      ]
    },
    {
      "conf_from": 0.98,
      "conf_to": 1.0,
      "n": 328,
      "hit": 0.9939,
      "ci": [
        0.978,
        0.998
      ]
    }
  ],
  "calibrated_on": "433 windows, 2026-09-27T23:15:00Z \u2192 2026-10-02T21:15:00Z",
  "calibrated_at": "2026-10-04T10:20:30Z"
}
```
