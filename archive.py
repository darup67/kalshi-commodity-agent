#!/usr/bin/env python3
"""Keep the live proxy's 1-minute history. Hyperliquid only serves ~3.5 days of 1m
candles, so this appends them to data/bars/<asset>-<YYYY-MM>.csv.gz (git-tracked).
backtest.py measures sigma_proxy on whatever overlap exists; this makes that
overlap grow every week, and gives a future backtest the REAL live price path.

    ~/.venvs/market-ml/bin/python archive.py
"""
import csv, gzip, json, os, time
import feeds

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = json.load(open(os.path.join(HERE, "assets.json")))


def main():
    now = int(time.time())
    for name, cfg in ASSETS.items():
        bars = feeds.hl_candles(cfg["hl_coin"], now - 4 * 86400, now - now % 60)
        by_month = {}
        for t, v in bars.items():
            by_month.setdefault(time.strftime("%Y-%m", time.gmtime(t)), {})[t] = v
        for month, rows in by_month.items():
            path = os.path.join(HERE, "data", "bars", f"{name}-{month}.csv.gz")
            have = {}
            if os.path.exists(path):
                with gzip.open(path, "rt") as f:
                    for r in csv.reader(f):
                        have[int(r[0])] = tuple(map(float, r[1:]))
            before = len(have)
            have.update(rows)
            if len(have) != before:
                with gzip.open(path, "wt") as f:
                    w = csv.writer(f)
                    for t in sorted(have):
                        w.writerow([t, *have[t]])
            print(f"{name} {month}: {before} -> {len(have)} bars")


if __name__ == "__main__":
    main()
