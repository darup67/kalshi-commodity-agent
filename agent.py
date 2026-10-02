#!/usr/bin/env python3
"""Kalshi gold / WTI 15-minute cushion caller. READ-ONLY: it never places an order.

The same idea as ~/kalshi-btc-agent for Kalshi's KXGOLD15M and KXWTI15M markets.
Every run (launchd, once a minute) it evaluates the open window of each asset and
logs the evaluation. It shows a call only when the gap since the window opened is
large against the volatility still to come (gate-<asset>.json, calibrated by
backtest.py). Everything else is NO CALL.

    agent.py [gold|wti]      print the card for the open window (no alert)
    agent.py --run           scheduled mode: log, settle, alert once per window
    agent.py --scorecard     live record of every call made so far, by asset and minute
"""
import json, math, os, random, subprocess, sys, time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statistics import NormalDist
import feeds, model

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = json.load(open(os.path.join(HERE, "assets.json")))
CONFIG = os.path.join(HERE, "config.json")
STATE = os.path.join(HERE, "data", "state.json")
ET = ZoneInfo("America/New_York")
MAX_BAR_AGE = 180  # seconds; an older last candle means the feed is stale or the market is closed
GIT = "/usr/local/bin/git"  # absolute: /usr/bin/git is Apple's stub and pops an install dialog without the CLT


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def evals_path(name):
    return os.path.join(HERE, "data", f"evals-{name}.jsonl")


def historical_hit(gate, conf):
    for row in gate.get("hit_table", []):
        if row["conf_from"] <= conf < row["conf_to"] + 1e-9:
            return row
    return None


def evaluate(name):
    cfg = ASSETS[name]
    gate = load(os.path.join(HERE, f"gate-{name}.json"), None)
    if not gate:
        sys.exit(f"gate-{name}.json missing — run backtest.py first")
    now = int(time.time())
    base = {"t": now, "asset": name}
    m = feeds.kalshi_open_window(cfg["series"])
    if not m:
        return {**base, "status": "no_window"}
    o_ts, c_ts = feeds.ts(m["open_time"]), feeds.ts(m["close_time"])
    ev = {**base, "ticker": m["ticker"], "open": m["open_time"], "close": m["close_time"],
          "strike": m.get("floor_strike"),
          "yes_bid": float(m.get("yes_bid_dollars") or 0), "yes_ask": float(m.get("yes_ask_dollars") or 0)}
    elapsed, left = (now - o_ts) / 60, (c_ts - now) / 60
    ev["minute"], ev["minutes_left"] = round(elapsed, 2), round(left, 2)
    if ev["strike"] is None:
        return {**ev, "status": "no_call", "why": "strike not published yet"}

    bars = feeds.hl_candles(cfg["hl_coin"], now - 3900, now)
    if not bars:
        return {**ev, "status": "no_call", "why": "no Hyperliquid candles"}
    last = max(bars)
    if now - last > MAX_BAR_AGE + 60:
        return {**ev, "status": "no_call", "why": f"price feed stale ({(now - last) / 60:.0f} min old)"}
    ref = bars.get(o_ts - 60)
    if not ref:
        return {**ev, "status": "no_call", "why": "no price at the window open"}
    spot = feeds.hl_mid(cfg["hl_coin"])
    ev["spot"] = round(spot, 4)
    ev["gap"] = round(spot - ref[3], 4)
    closes = [bars[t][3] for t in sorted(bars) if o_ts - 3600 <= t < now - now % 60]
    if len(closes) < 40:
        return {**ev, "status": "no_call", "why": "not enough 1m history for volatility"}
    d = [b - a for a, b in zip(closes, closes[1:])]
    mu = sum(d) / len(d)
    sig = math.sqrt(sum((x - mu) ** 2 for x in d) / len(d))
    p, sd = model.p_yes(ev["gap"], left, sig, gate["sigma_proxy"])
    side = "UP" if p >= 0.5 else "DOWN"
    conf = p if side == "UP" else 1 - p
    ev.update({"sigma_1m": round(sig, 4), "sd_to_close": round(sd, 4), "p_yes": round(p, 4), "side": side,
               "conf": round(conf, 4), "z": round(abs(ev["gap"]) / sd, 2),
               "range_15m": round(sig * math.sqrt(8 / math.pi) * math.sqrt(15), 3)})
    ask = ev["yes_ask"] if side == "UP" else 1 - ev["yes_bid"]
    ev["ask"] = round(ask, 4)

    if elapsed < gate["min_minute"]:
        return {**ev, "status": "no_call", "why": f"only {elapsed:.1f} min in; cushion not formed yet (gate starts at minute {gate['min_minute']})"}
    if left < 1:
        return {**ev, "status": "no_call", "why": "under a minute left"}
    min_conf = load(CONFIG, {}).get(name, {}).get("min_conf_override") or gate["min_conf"]
    min_z = NormalDist().inv_cdf(min_conf)
    if conf < min_conf:
        need = min_z * sd
        dec = cfg["decimals"]
        return {**ev, "status": "no_call",
                "why": f"cushion {abs(ev['gap']):.{dec}f} = {ev['z']:.2f}σ, gate needs {min_z:.2f}σ "
                       f"({cfg['label']} above ${spot - ev['gap'] + need:,.{dec}f} or below ${spot - ev['gap'] - need:,.{dec}f} on the proxy)"}
    h = historical_hit(gate, conf)
    ev["hist_hit"] = h["hit"] if h else None
    ev["hist_n"] = h["n"] if h else None
    if h and 0 < ask < 1:
        ev["edge"] = round(h["hit"] - ask - model.kalshi_fee(ask), 4)
    return {**ev, "status": "call"}


def fmt_et(iso):
    return datetime.fromtimestamp(feeds.ts(iso), tz=timezone.utc).astimezone(ET).strftime("%-I:%M %p")


def card(ev):
    cfg = ASSETS[ev["asset"]]
    dec = cfg["decimals"]
    if ev.get("status") == "no_window":
        return f"No open {cfg['series']} window."
    win = f"{fmt_et(ev['open'])}–{fmt_et(ev['close'])} ET"
    head = f"{cfg['label']} 15m · window {win} · minute {ev['minute']:.0f} of 15 · proxy Hyperliquid {cfg['hl_coin']} (settles on Pyth)"
    rows = [("Strike", f"${ev['strike']:,.{dec}f}" if ev.get("strike") else "—")]
    if "spot" in ev:
        rows.append((f"Current {cfg['label']}", f"${ev['spot']:,.{dec}f} on the proxy ({ev['gap']:+,.{dec}f} since the open)"))
    if "sd_to_close" in ev:
        rows.append(("Cushion", f"{ev['z']:.2f}σ — {abs(ev['gap']):,.{dec}f} vs ±{ev['sd_to_close']:,.{dec}f} to close"))
    if ev["status"] != "call":
        rows.append(("Call", "NO CALL"))
        rows.append(("Why", ev.get("why", "")))
        if "range_15m" in ev:
            rows.append(("Volatility", f"{ev['range_15m']:,.{dec}f} expected 15m range (60-min realized)"))
    else:
        rows.append(("P(" + ("above" if ev["side"] == "UP" else "below") + " strike)",
                     f"model {ev['conf']:.1%} · calls like this won {ev['hist_hit']:.1%} (n={ev['hist_n']})"))
        rows.append(("Call", f"{ev['side']} — {ev['hist_hit']:.0%}"))
        rows.append(("Volatility", f"{ev['range_15m']:,.{dec}f} expected 15m range (60-min realized)"))
        rows.append(("Kalshi ask", f"{ev['side']} side {ev['ask'] * 100:.0f}¢"))
        e = ev.get("edge")
        if e is not None:
            rows.append(("Edge vs ask", f"{e * 100:+.1f}¢ after fee — " + ("priced in, no edge" if e <= 0 else "positive, unproven (backtest CI spans 0)")))
    w = max(len(r[0]) for r in rows)
    return head + "\n\n" + "\n".join(f"  {k.ljust(w)}  {v}" for k, v in rows)


def notify(ev, cfg):
    """Banner title carries the call (this Mac hides notification bodies); sound is the reliable channel."""
    a = ASSETS[ev["asset"]]
    title = f"{a['label'].upper()} {fmt_et(ev['close'])} {ev['side']} {ev['hist_hit']:.0%} · ask {ev['ask'] * 100:.0f}¢"
    def run(cmd):
        try:
            subprocess.run(cmd, capture_output=True, timeout=20)
        except Exception as e:
            print(f"alert channel {cmd[0]} failed: {e}", file=sys.stderr)
    if cfg.get("banner", False):
        run(["/usr/bin/osascript", "-e", f'display notification "" with title "{title}"'])
    if cfg.get("sound", False):
        run(["/usr/bin/afplay", "/System/Library/Sounds/Glass.aiff"])


def settle(name, state):
    pending = state.setdefault("pending", {}).setdefault(name, {})
    for ticker, rec in list(pending.items()):
        if time.time() < feeds.ts(rec["close"]) + 120:
            continue
        try:
            mk = feeds.kalshi_market(ticker)
        except Exception:
            continue
        if mk.get("result") not in ("yes", "no"):
            continue
        won = (mk["result"] == "yes") == (rec["side"] == "UP")
        with open(evals_path(name), "a") as f:
            f.write(json.dumps({"t": int(time.time()), "asset": name, "ticker": ticker, "status": "settled",
                                "result": mk["result"], "side": rec["side"], "won": won, "conf": rec["conf"],
                                "hist_hit": rec["hist_hit"], "ask": rec["ask"]}) + "\n")
        pending.pop(ticker)


def run():
    cfgs = load(CONFIG, {})
    state = load(STATE, {})
    for name in ASSETS:
        try:
            settle(name, state)
        except Exception as e:
            print(f"{name} settle: {e}", file=sys.stderr)
        try:
            ev = evaluate(name)
        except SystemExit as e:
            print(f"{name}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"{name} evaluate: {e!r}", file=sys.stderr)
            continue
        if ev.get("status") != "no_window":
            with open(evals_path(name), "a") as f:
                f.write(json.dumps(ev) + "\n")
        if ev.get("status") == "call":
            alerted = state.setdefault("alerted", {}).setdefault(name, {})
            if alerted.get(ev["ticker"]) != ev["side"]:
                alerted[ev["ticker"]] = ev["side"]
                state.setdefault("pending", {}).setdefault(name, {})[ev["ticker"]] = {
                    k: ev[k] for k in ("close", "side", "conf", "hist_hit", "ask")}
                notify(ev, cfgs.get(name, {}).get("alerts", {}))
                print(card(ev))
            state["alerted"][name] = {k: v for k, v in alerted.items()
                                      if k == ev["ticker"] or k in state["pending"].get(name, {})}
    json.dump(state, open(STATE, "w"), indent=1)
    try:
        autocommit()
    except Exception as e:
        print(f"autocommit: {e!r}", file=sys.stderr)


def autocommit():
    """Hourly: commit and push the evals logs. Acts only when they are dirty and the last commit is an
    hour old; a git failure (index.lock held by recal.sh, no network) is logged and retried next minute."""
    def git(*a):
        r = subprocess.run([GIT, *a], cwd=HERE, capture_output=True, text=True, timeout=60)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    paths = [f"data/evals-{n}.jsonl" for n in ASSETS]
    ok, out = git("status", "--porcelain", *paths)
    if not ok or not out:
        return
    ok, last = git("log", "-1", "--format=%ct", "--", *paths)
    if ok and last and time.time() - int(last) < 3600:
        return
    ok, out = git("add", *paths)
    if ok:
        ok, out = git("-c", "user.name=kalshi-commodity-agent", "-c", "user.email=darup67@gmail.com",
                      "commit", "-q", "-m", "data: evals logs", "--", *paths)
    if ok:
        ok, out = git("push", "-q", "origin", "HEAD")
    if not ok:
        print(f"autocommit: git failed: {out[-200:]}", file=sys.stderr)


def scorecard():
    for name, cfg in ASSETS.items():
        path = evals_path(name)
        rows = [json.loads(l) for l in open(path)] if os.path.exists(path) else []
        s = [r for r in rows if r.get("status") == "settled"]
        evals = [r for r in rows if r.get("status") in ("call", "no_call")]
        print(f"\n== {cfg['label']} ({cfg['series']}): {len(evals)} evaluations logged, {len(s)} calls settled")
        if not s:
            continue
        k = sum(r["won"] for r in s)
        brier = sum((r["hist_hit"] - r["won"]) ** 2 for r in s) / len(s)
        pnl = [int(r["won"]) - r["ask"] - model.kalshi_fee(min(max(r["ask"], .01), .99)) for r in s]
        print(f"hit rate {k}/{len(s)} = {k / len(s):.1%} · expected {sum(r['hist_hit'] for r in s) / len(s):.1%}"
              f" · Brier {brier:.4f} · paper EV at ask {sum(pnl) / len(pnl) * 100:+.1f}¢/contract (no orders placed)")
        first_call = {}
        for r in evals:
            if r["status"] == "call":
                first_call.setdefault(r["ticker"], r)
        by_min = {}
        for r, p in zip(s, pnl):
            c = first_call.get(r["ticker"])
            if c:
                by_min.setdefault(int(c["minute"]), []).append((r["won"], r["ask"], p))
        days = len({time.strftime("%Y-%m-%d", time.gmtime(r["t"])) for r in s})
        rng = random.Random(1)
        print(f"by minute of the first call in each window ({days} separate days; 95% range treats calls as independent, so it is too narrow):")
        print("  min    n   hit    ask   EV¢/contract   95% range")
        for m in sorted(by_min):
            v = by_min[m]
            n = len(v)
            pn = [x[2] for x in v]
            boot = sorted(sum(rng.choice(pn) for _ in range(n)) / n * 100 for _ in range(2000))
            print(f"  {m:>3} {n:>4} {sum(x[0] for x in v) / n:5.1%}  {sum(x[1] for x in v) / n:.2f}   {sum(pn) / n * 100:+8.1f}      [{boot[50]:+.1f}, {boot[1949]:+.1f}]")
        print("  Not proven until 10+ separate days of calls.")


if __name__ == "__main__":
    if "--run" in sys.argv:
        run()
    elif "--scorecard" in sys.argv:
        scorecard()
    else:
        picks = [a for a in sys.argv[1:] if a in ASSETS] or list(ASSETS)
        for n in picks:
            print(card(evaluate(n)))
            print()
