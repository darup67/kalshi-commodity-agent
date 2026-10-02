#!/usr/bin/env python3
"""Calibrate the cushion gate for the Kalshi gold / WTI 15-minute markets.

Same method as ~/kalshi-btc-agent/backtest.py, adapted to what is available:
  * windows + outcomes: Kalshi's settled markets (strike = Pyth price at the open,
    expiration_value = Pyth price at the close), kept forever in data/windows-<asset>.jsonl
  * price path: Yahoo CME futures 1m bars, the last ~7 days (history only; they are
    10 minutes delayed live, so the live agent uses Hyperliquid instead)
  * sigma_proxy: how far the LIVE proxy (Hyperliquid) was from Pyth's window change,
    measured on the Hyperliquid 1m history that overlaps (~3.5 days; archive.py keeps
    growing it so this sharpens every week)
  * market price at each minute: Kalshi's own candlesticks (clock-aligned YES bid/ask)

The gate rule is the BTC one, fixed in advance: the lowest confidence whose fit-half
hit rate has a Wilson lower bound >= 90% (n >= 30), reported on the held-out half.
Minute-by-minute cells are hypotheses for the live scorecard, not findings.

    ~/.venvs/market-ml/bin/python backtest.py [gold|wti ...]
"""
import json, math, os, sys, time
from datetime import datetime, timezone
from statistics import NormalDist
import numpy as np
import feeds, model

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = json.load(open(os.path.join(HERE, "assets.json")))
CHECKPOINTS = [3, 5, 7, 9, 11, 13]
P_GRID = [0.80, 0.85, 0.90, 0.93, 0.95, 0.97, 0.98, 0.99]
TARGET_HIT, MIN_N = 0.90, 30


def save_windows(name, markets):
    """Append-only history of every settled window (Kalshi's API does not keep them forever)."""
    path = os.path.join(HERE, "data", f"windows-{name}.jsonl")
    have = {json.loads(l)["ticker"] for l in open(path)} if os.path.exists(path) else set()
    new = 0
    with open(path, "a") as f:
        for m in sorted(markets, key=lambda m: m["close_time"]):
            if m["ticker"] in have or m.get("result") not in ("yes", "no") or m.get("floor_strike") is None:
                continue
            f.write(json.dumps({"ticker": m["ticker"], "open_time": m["open_time"], "close_time": m["close_time"],
                                "strike": m["floor_strike"], "settle": m.get("expiration_value"),
                                "result": m["result"]}) + "\n")
            new += 1
    return new


def market_candles(name, series, ws):
    cache = os.path.join(HERE, "data", f"kalshi-candles-{name}.json")
    have = json.load(open(cache)) if os.path.exists(cache) else {}
    todo = [w for w in ws if w["ticker"] not in have]
    for n, w in enumerate(todo):
        try:
            have[w["ticker"]] = feeds.kalshi_candles(series, w["ticker"], w["o_ts"], w["c_ts"])
        except Exception:
            continue
        if n % 100 == 99:
            json.dump(have, open(cache, "w"))
            print(f"  {name} kalshi candles {n + 1}/{len(todo)}", file=sys.stderr)
        time.sleep(0.12)
    json.dump(have, open(cache, "w"))
    return have


def measure_sigma_proxy(cfg, ws, hl):
    """RMS of (Pyth window change - Hyperliquid window change) over overlapping windows."""
    e = []
    for w in ws:
        a, b = hl.get(w["o_ts"] - 60), hl.get(w["c_ts"] - 60)
        if a and b and w["settle"] is not None:
            e.append((w["settle"] - w["strike"]) - (b[3] - a[3]))
    return (float(np.sqrt(np.mean(np.square(e)))), len(e)) if len(e) >= 100 else (cfg["sigma_proxy_default"], len(e))


def run(name):
    cfg = ASSETS[name]
    series = cfg["series"]
    now = int(time.time())
    bars = feeds.yahoo_1m(cfg["yahoo"])
    t0 = min(bars)
    settled = feeds.kalshi_settled(series)               # whole history, for the permanent archive
    new = save_windows(name, settled)
    ws = []
    for m in settled:
        if m.get("result") not in ("yes", "no") or m.get("floor_strike") is None or m.get("expiration_value") in (None, ""):
            continue
        w = {"ticker": m["ticker"], "o_ts": feeds.ts(m["open_time"]), "c_ts": feeds.ts(m["close_time"]),
             "open_time": m["open_time"], "close_time": m["close_time"], "strike": float(m["floor_strike"]),
             "settle": float(m["expiration_value"]), "y": int(m["result"] == "yes")}
        if w["o_ts"] - 3700 >= t0:
            ws.append(w)
    ws.sort(key=lambda w: w["o_ts"])
    hl = feeds.hl_candles(cfg["hl_coin"], now - 4 * 86400, now)
    sig_p, n_p = measure_sigma_proxy(cfg, ws, hl)
    # also: how well CME futures (the backtest price path) track Pyth
    yerr = [(w["settle"] - w["strike"]) - (bars[w["c_ts"] - 60][3] - bars[w["o_ts"] - 60][3])
            for w in ws if w["c_ts"] - 60 in bars and w["o_ts"] - 60 in bars]
    cd = {t: v for t, v in bars.items()}
    MK = market_candles(name, series, ws)

    lines = [f"# {cfg['label']} 15-minute backtest — {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
             f"Series {series}, settles on {cfg['settles_on']}.",
             f"{len(ws)} settled windows with a CME price path ({ws[0]['open_time']} → {ws[-1]['close_time']}); "
             f"{new} new windows added to the permanent archive (data/windows-{name}.jsonl, {len(settled)} on Kalshi now).", "",
             "## 1. Proxy error against Pyth (change over a 15-minute window)", "",
             "| proxy | windows | RMS error $ | role |", "|---|---|---|---|",
             f"| Hyperliquid {cfg['hl_coin']} | {n_p} | {sig_p:.3f} | LIVE proxy; this is sigma_proxy in the model |",
             f"| Yahoo CME {cfg['yahoo']} | {len(yerr)} | {float(np.sqrt(np.mean(np.square(yerr)))):.3f} | backtest price path only (delayed live) |", ""]

    obs, usable = [], []
    for w in ws:
        closes = [cd[t][3] for t in range(w["o_ts"] - 3600, w["o_ts"], 60) if t in cd]
        ref = cd.get(w["o_ts"] - 60)
        if len(closes) < 40 or not ref:
            continue
        w["sig"] = float(np.std(np.diff(closes)))
        w["ref"] = ref[3]
        usable.append(w)
    for i, w in enumerate(usable):
        for m in CHECKPOINTS:
            k = cd.get(w["o_ts"] + (m - 1) * 60)
            q = MK.get(w["ticker"], {}).get(str(w["o_ts"] + m * 60))
            if not k or not q or not (0 < q[0] <= q[1] < 1):
                continue
            gap = k[3] - w["ref"]
            p, sd = model.p_yes(gap, 15 - m, w["sig"], sig_p)
            obs.append({"i": i, "m": m, "gap": gap, "y": w["y"], "p": p, "mkt": (q[0] + q[1]) / 2,
                        "ask_yes": q[1], "ask_no": 1 - q[0]})
    half = len(usable) // 2
    A = [o for o in obs if o["i"] < half]
    B = [o for o in obs if o["i"] >= half]
    br = lambda os_, key: float(np.mean([(o[key] - o["y"]) ** 2 for o in os_])) if os_ else float("nan")
    lines += ["## 2. Calibration (Brier, lower is better; all checkpoints)", "",
              "| source | fit half | test half |", "|---|---|---|",
              f"| gap / realized vol | {br(A, 'p'):.4f} | {br(B, 'p'):.4f} |",
              f"| Kalshi mid at the same minute | {br(A, 'mkt'):.4f} | {br(B, 'mkt'):.4f} |", ""]

    def calls(os_, pmin):
        out = []
        for o in os_:
            side_yes = o["p"] >= 0.5
            conf = o["p"] if side_yes else 1 - o["p"]
            if conf >= pmin:
                out.append((o["y"] == int(side_yes), conf, o["ask_yes"] if side_yes else o["ask_no"], o))
        return out

    ev_of = lambda cs: float(np.mean([x[0] - x[2] - model.kalshi_fee(min(max(x[2], .01), .99)) for x in cs])) if cs else float("nan")
    lines += ["## 3. Gate sweep", "",
              "Call = the side the model favours, only when its confidence clears the bar. `paid` = Kalshi ask for that "
              "side at that minute. `EV/contract` = win − paid − fee; positive means the call beat the market.", "",
              "| min conf | fit n | fit hit [95% CI] | test n | test hit [95% CI] | test avg conf | test avg paid | test EV/contract |",
              "|---|---|---|---|---|---|---|---|"]
    chosen = None
    for pmin in P_GRID:
        a, b = calls(A, pmin), calls(B, pmin)
        ka, kb = sum(x[0] for x in a), sum(x[0] for x in b)
        la, ha = model.wilson(ka, len(a))
        lb, hb = model.wilson(kb, len(b))
        lines.append(f"| {pmin:.2f} | {len(a)} | {ka / max(len(a), 1):.1%} [{la:.0%}–{ha:.0%}] | {len(b)} | "
                     f"{kb / max(len(b), 1):.1%} [{lb:.0%}–{hb:.0%}] | "
                     f"{np.mean([x[1] for x in b]) if b else float('nan'):.1%} | "
                     f"{np.mean([x[2] for x in b]) if b else float('nan'):.2f} | {ev_of(b):+.3f} |")
        if chosen is None and len(a) >= MIN_N and la >= TARGET_HIT:
            chosen = pmin
    chosen = chosen or P_GRID[-1]
    zc = NormalDist().inv_cdf(chosen)

    lines += ["", f"## 4. At the chosen gate ({chosen:.2f}), by minute into the window (test half)", "",
              "EV 95% CI is a bootstrap over calls (calls cluster in time, so it is too narrow); cells were not pre-registered.", "",
              "| minute | calls | hit | avg ask paid | EV/contract [95% CI] | median cushion $ |", "|---|---|---|---|---|---|"]
    rng_ = np.random.default_rng(7)
    for m in CHECKPOINTS:
        b = [x for x in calls(B, chosen) if x[3]["m"] == m]
        if not b:
            lines.append(f"| {m} | 0 | — | — | — | — |")
            continue
        pnl = np.array([x[0] - x[2] - model.kalshi_fee(min(max(x[2], .01), .99)) for x in b])
        bs = [rng_.choice(pnl, len(pnl)).mean() for _ in range(2000)]
        lines.append(f"| {m} | {len(b)} | {np.mean([x[0] for x in b]):.1%} | {np.mean([x[2] for x in b]):.2f} | "
                     f"{pnl.mean():+.3f} [{np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}] | "
                     f"{np.median([abs(x[3]['gap']) for x in b]):.2f} |")

    hit_table, edges, allc = [], [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.98, 1.0001], calls(A + B, 0.50)
    for lo, hi in zip(edges, edges[1:]):
        sel = [x for x in allc if lo <= x[1] < hi]
        if sel:
            k = sum(x[0] for x in sel)
            l, h = model.wilson(k, len(sel))
            hit_table.append({"conf_from": lo, "conf_to": min(hi, 1.0), "n": len(sel),
                              "hit": round(k / len(sel), 4), "ci": [round(l, 3), round(h, 3)]})
    gate = {"asset": name, "series": series, "sigma_proxy": round(sig_p, 4), "min_conf": chosen, "min_z": round(zc, 2),
            "min_minute": 3, "hit_table": hit_table,
            "calibrated_on": f"{len(usable)} windows, {usable[0]['open_time']} → {usable[-1]['close_time']}",
            "calibrated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    json.dump(gate, open(os.path.join(HERE, f"gate-{name}.json"), "w"), indent=2)
    lines += ["", f"## gate-{name}.json", "", "```json", json.dumps(gate, indent=2), "```"]
    out = os.path.join(HERE, "results", f"backtest-{name}-{datetime.now().strftime('%Y-%m-%d')}.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}", file=sys.stderr)


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(ASSETS)):
        run(n)
