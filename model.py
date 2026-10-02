"""The call model, shared by backtest.py and agent.py so the live agent runs
exactly what was calibrated. Same idea as ~/kalshi-btc-agent: direction is not
forecast; a call is the gap already on the board over the volatility still to come.

  P(YES) = Phi( gap / sqrt(sigma_1m^2 * minutes_left + sigma_proxy^2) )

gap          proxy now minus proxy at the window open (the strike is the Pyth
             price at the open, so the level basis between proxy and Pyth cancels)
minutes_left settlement is ONE Pyth 1-minute candle close, not a 60-second
             average, so there is no BTC-style "minus 2/3 minute" adjustment
sigma_1m     $ per sqrt(minute), std of the last 60 one-minute close changes
sigma_proxy  measured error of the proxy's window change vs Pyth's, $
"""
import math


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def p_yes(gap, minutes_left, sigma_1m, sigma_proxy):
    r_eff = max(minutes_left, 0.2)
    sd = math.sqrt(sigma_1m ** 2 * r_eff + sigma_proxy ** 2)
    return phi(gap / sd), sd


def kalshi_fee(price):
    """Kalshi taker fee per contract, $: ceil(0.07 * P * (1-P) * 100) cents."""
    return math.ceil(0.07 * price * (1 - price) * 100 - 1e-9) / 100


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h
