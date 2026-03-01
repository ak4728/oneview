"""
bnb_collector.py

Collect 1-minute BNB prices by polling Robinhood's best_bid_ask endpoint,
aggregate to 1-minute OHLC, compute Supertrend, and save CSV + chart.

Usage (real):
  - Set ROBINHOOD_TOKEN in env if required by endpoint (optional)
  - Run: python bnb_collector.py --minutes 10

Usage (quick local test):
  - Run with `--mock` to generate synthetic ticks and test the pipeline.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import time
from typing import Optional

import os
import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from indicators import compute_supertrend


class BNBCollector:
    def __init__(self, auth_token: Optional[str] = None, base_url: str = "https://trading.robinhood.com"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({"Authorization": f"Token {auth_token}"})

    def _fetch_tick(self, symbol: str = "BNB") -> Optional[dict]:
        """Fetch best bid/ask for `symbol`. Returns dict with timestamp, bid, ask, mid."""
        path = f"/api/v1/crypto/marketdata/best_bid_ask/"
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params={"symbols": symbol}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Response shape: {'results': [{...}]}
            res = data.get('results') or []
            if not res:
                return None
            r = res[0]
            bid = r.get('bid')
            ask = r.get('ask')
            # some endpoints provide nested best_bid and best_ask
            if bid is None and 'best_bid' in r:
                bid = r['best_bid']
            if ask is None and 'best_ask' in r:
                ask = r['best_ask']

            if bid is None or ask is None:
                return None

            mid = (float(bid) + float(ask)) / 2.0
            return {"ts": dt.datetime.utcnow(), "bid": float(bid), "ask": float(ask), "mid": mid}
        except Exception:
            return None

    def collect(self, minutes: int = 10, poll_interval: float = 5.0, symbol: str = "BNBUSD", use_mock: bool = False, source: str = "robinhood", exchange: str = "BINANCE") -> pd.DataFrame:
        """Collect ticks for `minutes`, poll every `poll_interval` seconds.

        source: 'robinhood' (default) | 'tradingview' | 'mock'

        If `use_mock` is True or `source=='mock'`, generate synthetic ticks for testing.
        Returns a DataFrame of 1-minute OHLCV indexed by minute timestamp.
        """
        end_time = time.time() + minutes * 60.0
        samples = []
        rng = np.random.default_rng(42)

        # tradingview handler prepared lazily
        tv_handler = None
        if source == 'tradingview' and not use_mock:
            try:
                from tradingview_ta import TA_Handler, Interval

                # allow passing arbitrary symbol/exchange (e.g., BNBUSD on BINANCE or COINBASE)
                tv_handler = TA_Handler(symbol=symbol, screener="crypto", exchange=exchange, interval=Interval.INTERVAL_1_MINUTE)
            except Exception:
                tv_handler = None

        while time.time() < end_time:
            ts = dt.datetime.utcnow()
            if use_mock or source == 'mock':
                # synthetic tick: random walk around 300
                price = 300.0 + rng.normal(0, 0.5)
                bid = price - 0.01 * abs(rng.normal())
                ask = price + 0.01 * abs(rng.normal())
                mid = price
                samples.append({"ts": ts, "bid": float(bid), "ask": float(ask), "mid": float(mid), "volume": int(rng.integers(1, 100))})
            elif source == 'tradingview' and tv_handler is not None:
                try:
                    ana = tv_handler.get_analysis()
                    # try common indicator names for close
                    close_val = None
                    for key in ("close", "CLOSE", "Close"):
                        close_val = ana.indicators.get(key) if hasattr(ana, 'indicators') else None
                        if close_val is not None:
                            break
                    # if indicators don't have close, try summary price
                    if close_val is None:
                        # some builds expose a 'indicators' dict with 'open' etc; attempt best effort
                        close_val = ana.indicators.get('close') if hasattr(ana, 'indicators') else None
                    if close_val is None:
                        # fallback: try to use the 'price' attribute
                        close_val = getattr(ana, 'price', None)
                    if close_val is None:
                        # last resort: skip this tick
                        time.sleep(poll_interval)
                        continue
                    mid = float(close_val)
                    samples.append({"ts": ts, "bid": mid * 0.999, "ask": mid * 1.001, "mid": mid, "volume": 0})
                except Exception:
                    # on any failure, fallback to a short sleep and continue
                    time.sleep(poll_interval)
                    continue
            else:
                tick = self._fetch_tick(symbol)
                if tick is not None:
                    tick['volume'] = 0
                    samples.append(tick)

            time.sleep(poll_interval)

        if not samples:
            raise RuntimeError("No ticks collected")

        # Build DataFrame of ticks
        df_ticks = pd.DataFrame(samples)
        df_ticks.set_index(pd.to_datetime(df_ticks['ts']), inplace=True)

        # Resample to 1-minute OHLC
        ohlc = df_ticks['mid'].resample('1min').ohlc()
        # For volume, sum the mock/0 volumes
        if 'volume' in df_ticks.columns:
            vol = df_ticks['volume'].resample('1min').sum().fillna(0)
        else:
            vol = pd.Series(0, index=ohlc.index)

        ohlc = ohlc.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'})
        ohlc['volume'] = vol

        # Drop minutes with no data
        ohlc = ohlc.dropna(subset=['close'])

        return ohlc


def save_csv(df: pd.DataFrame, path: Optional[str] = None) -> str:
    if path is None:
        path = os.path.join(os.getcwd(), f"bnb_{dt.datetime.utcnow():%Y%m%d_%H%M%S}.csv")
    df.to_csv(path)
    return path


def plot_with_supertrend(df: pd.DataFrame, out_path: Optional[str] = None) -> str:
    st = compute_supertrend(df[['open', 'high', 'low', 'close']].copy(), period=10, multiplier=3.0, change_atr=True)
    for k, v in st.items():
        df[k] = v

    if out_path is None:
        out_path = os.path.join(os.getcwd(), f"bnb_supertrend_{dt.datetime.utcnow():%Y%m%d_%H%M%S}.png")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df['close'], label='Close', color='k')
    ax.plot(df.index, df['ST_up'], label='ST_up', color='green')
    ax.plot(df.index, df['ST_dn'], label='ST_dn', color='red')
    buys = df[df['ST_buy'] == True]
    sells = df[df['ST_sell'] == True]
    if not buys.empty:
        ax.scatter(buys.index, buys['close'], marker='^', color='green', label='Buy', zorder=5)
    if not sells.empty:
        ax.scatter(sells.index, sells['close'], marker='v', color='red', label='Sell', zorder=5)

    ax.set_title('BNB 1-min Supertrend')
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--minutes', type=int, default=10, help='Minutes to collect')
    parser.add_argument('--interval', type=float, default=5.0, help='Poll interval seconds')
    parser.add_argument('--mock', action='store_true', help='Use synthetic ticks (quick test)')
    parser.add_argument('--save', action='store_true', help='Save CSV and chart')
    parser.add_argument('--source', choices=['robinhood', 'tradingview', 'mock'], default='robinhood', help='Data source')
    parser.add_argument('--symbol', type=str, default='BNBUSD', help='Symbol to collect (e.g., BNBUSD, BNBUSDT)')
    parser.add_argument('--exchange', type=str, default='BINANCE', help='Exchange to query when using tradingview source')
    args = parser.parse_args()

    token = os.environ.get('ROBINHOOD_TOKEN')
    collector = BNBCollector(auth_token=token)
    print(f"Collecting for {args.minutes} minutes (source={args.source}, symbol={args.symbol}, mock={args.mock})...")
    df = collector.collect(minutes=args.minutes, poll_interval=args.interval, use_mock=args.mock, source=args.source, symbol=args.symbol, exchange=args.exchange)
    print('Collected', len(df), '1-min bars')

    if args.save:
        csv_path = save_csv(df)
        print('Saved CSV to', csv_path)
        img = plot_with_supertrend(df)
        print('Saved chart to', img)


if __name__ == '__main__':
    main()
