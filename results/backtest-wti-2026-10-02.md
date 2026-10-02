# WTI oil 15-minute backtest — 2026-10-02 09:49

Series KXWTI15M, settles on Pyth PYTHOIL/USD, 1-minute candle close.
530 settled windows with a CME price path (2026-09-25T05:15:00Z → 2026-10-02T13:45:00Z); 4407 new windows added to the permanent archive (data/windows-wti.jsonl, 4414 on Kalshi now).

## 1. Proxy error against Pyth (change over a 15-minute window)

| proxy | windows | RMS error $ | role |
|---|---|---|---|
| Hyperliquid xyz:CL | 333 | 0.019 | LIVE proxy; this is sigma_proxy in the model |
| Yahoo CME CL=F | 466 | 0.022 | backtest price path only (delayed live) |

## 2. Calibration (Brier, lower is better; all checkpoints)

| source | fit half | test half |
|---|---|---|
| gap / realized vol | 0.1426 | 0.1699 |
| Kalshi mid at the same minute | 0.1398 | 0.1689 |

## 3. Gate sweep

Call = the side the model favours, only when its confidence clears the bar. `paid` = Kalshi ask for that side at that minute. `EV/contract` = win − paid − fee; positive means the call beat the market.

| min conf | fit n | fit hit [95% CI] | test n | test hit [95% CI] | test avg conf | test avg paid | test EV/contract |
|---|---|---|---|---|---|---|---|
| 0.80 | 554 | 95.8% [94%–97%] | 512 | 92.2% [90%–94%] | 92.6% | 0.92 | -0.012 |
| 0.85 | 456 | 96.3% [94%–98%] | 415 | 95.2% [93%–97%] | 94.9% | 0.94 | -0.000 |
| 0.90 | 362 | 97.8% [96%–99%] | 332 | 96.4% [94%–98%] | 96.8% | 0.95 | -0.000 |
| 0.93 | 306 | 98.7% [97%–99%] | 272 | 98.2% [96%–99%] | 97.9% | 0.96 | +0.008 |
| 0.95 | 262 | 98.9% [97%–100%] | 231 | 98.7% [96%–100%] | 98.6% | 0.97 | +0.008 |
| 0.97 | 213 | 99.1% [97%–100%] | 179 | 98.9% [96%–100%] | 99.3% | 0.98 | +0.001 |
| 0.98 | 194 | 100.0% [98%–100%] | 162 | 99.4% [97%–100%] | 99.5% | 0.98 | +0.003 |
| 0.99 | 168 | 100.0% [98%–100%] | 127 | 100.0% [97%–100%] | 99.8% | 0.98 | +0.005 |

## 4. At the chosen gate (0.80), by minute into the window (test half)

EV 95% CI is a bootstrap over calls (calls cluster in time, so it is too narrow); cells were not pre-registered.

| minute | calls | hit | avg ask paid | EV/contract [95% CI] | median cushion $ |
|---|---|---|---|---|---|
| 3 | 32 | 84.4% | 0.86 | -0.029 [-0.159, +0.091] | 0.29 |
| 5 | 46 | 84.8% | 0.87 | -0.030 [-0.134, +0.063] | 0.25 |
| 7 | 79 | 89.9% | 0.89 | -0.006 [-0.077, +0.055] | 0.22 |
| 9 | 92 | 91.3% | 0.92 | -0.019 [-0.078, +0.032] | 0.22 |
| 11 | 121 | 93.4% | 0.94 | -0.012 [-0.059, +0.029] | 0.20 |
| 13 | 142 | 97.2% | 0.96 | -0.001 [-0.029, +0.023] | 0.19 |

## gate-wti.json

```json
{
  "asset": "wti",
  "series": "KXWTI15M",
  "sigma_proxy": 0.0185,
  "min_conf": 0.8,
  "min_z": 0.84,
  "min_minute": 3,
  "hit_table": [
    {
      "conf_from": 0.5,
      "conf_to": 0.6,
      "n": 682,
      "hit": 0.5572,
      "ci": [
        0.52,
        0.594
      ]
    },
    {
      "conf_from": 0.6,
      "conf_to": 0.7,
      "n": 572,
      "hit": 0.6329,
      "ci": [
        0.593,
        0.671
      ]
    },
    {
      "conf_from": 0.7,
      "conf_to": 0.8,
      "n": 450,
      "hit": 0.7867,
      "ci": [
        0.746,
        0.822
      ]
    },
    {
      "conf_from": 0.8,
      "conf_to": 0.85,
      "n": 195,
      "hit": 0.8667,
      "ci": [
        0.812,
        0.907
      ]
    },
    {
      "conf_from": 0.85,
      "conf_to": 0.9,
      "n": 177,
      "hit": 0.904,
      "ci": [
        0.852,
        0.939
      ]
    },
    {
      "conf_from": 0.9,
      "conf_to": 0.95,
      "n": 201,
      "hit": 0.9303,
      "ci": [
        0.886,
        0.958
      ]
    },
    {
      "conf_from": 0.95,
      "conf_to": 0.98,
      "n": 137,
      "hit": 0.9635,
      "ci": [
        0.917,
        0.984
      ]
    },
    {
      "conf_from": 0.98,
      "conf_to": 1.0,
      "n": 356,
      "hit": 0.9972,
      "ci": [
        0.984,
        1.0
      ]
    }
  ],
  "calibrated_on": "468 windows, 2026-09-25T05:15:00Z \u2192 2026-10-02T13:45:00Z",
  "calibrated_at": "2026-10-02T13:49:18Z"
}
```
