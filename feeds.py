"""Price feeds and Kalshi access for the gold / WTI 15-minute markets.

Kalshi settles these on a Pyth 1-minute candle close (window close vs window
open). Pyth's own price API now needs a key, so the live proxy is Hyperliquid's
real-time gold and WTI perpetuals (keyless, 24/7); the historical proxy for
backtests is Yahoo's CME futures bars (10 minutes delayed live, so never used
for live calls). Only CHANGES since the window open matter, because the
strike is the Pyth price at the open: gap = proxy now - proxy at the open.
"""
import json, time, urllib.request, urllib.parse
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
HL = "https://api.hyperliquid.xyz/info"


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.load(r)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(1.5 * (k + 1))


def post(url, body, tries=3):
    data = json.dumps(body).encode()
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(1.5 * (k + 1))


def iso(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ts(s):
    return int(datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


# ── live proxy: Hyperliquid ────────────────────────────────────────────────
def hl_candles(coin, start, end):
    """{minute_start_ts: (o,h,l,c)}; the endpoint returns at most ~5000 recent 1m candles."""
    out, s = {}, start
    while s < end:
        e = min(s + 4000 * 60, end)
        for c in post(HL, {"type": "candleSnapshot", "req": {"coin": coin, "interval": "1m",
                                                              "startTime": s * 1000, "endTime": e * 1000}}):
            out[c["t"] // 1000] = (float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"]))
        s = e
        time.sleep(0.25)
    return out


def hl_mid(coin):
    mids = post(HL, {"type": "allMids", "dex": coin.split(":")[0]})
    return float(mids[coin])


# ── historical proxy: Yahoo CME futures (backtests only) ───────────────────
def yahoo_1m(sym, rng="7d"):
    j = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym, safe='')}"
            f"?interval=1m&range={rng}&includePrePost=true")["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    return {t: (o, h, l, c) for t, o, h, l, c in zip(j["timestamp"], q["open"], q["high"], q["low"], q["close"])
            if c is not None}


# ── Kalshi ─────────────────────────────────────────────────────────────────
def kalshi_open_window(series):
    ms = sorted(get(f"{KALSHI}/markets?series_ticker={series}&status=open&limit=5").get("markets", []),
                key=lambda m: m["close_time"])
    return ms[0] if ms else None


def kalshi_market(ticker):
    return get(f"{KALSHI}/markets/{ticker}")["market"]


def kalshi_settled(series, min_close_ts=None):
    out, cur = [], None
    while True:
        u = f"{KALSHI}/markets?series_ticker={series}&status=settled&limit=1000"
        if min_close_ts:
            u += f"&min_close_ts={min_close_ts}"
        if cur:
            u += f"&cursor={cur}"
        j = get(u)
        out += j["markets"]
        cur = j.get("cursor")
        if not cur or not j["markets"]:
            return out


def kalshi_candles(series, ticker, o_ts, c_ts):
    """{end_period_ts_str: (yes_bid_close, yes_ask_close)} for one window."""
    j = get(f"{KALSHI}/series/{series}/markets/{ticker}/candlesticks"
            f"?start_ts={o_ts}&end_ts={c_ts}&period_interval=1")
    bars = {}
    for c in j.get("candlesticks", []):
        b, a = c.get("yes_bid", {}).get("close_dollars"), c.get("yes_ask", {}).get("close_dollars")
        if b is not None and a is not None:
            bars[str(c["end_period_ts"])] = (float(b), float(a))
    return bars
