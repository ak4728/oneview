import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def fetch_ohlcv(symbol: str, interval: str = '1d', years: int = 5) -> pd.DataFrame:
    end = datetime.utcnow()
    start = end - timedelta(days=365 * years)
    df = yf.download(symbol, start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), interval=interval, progress=False)
    if df.empty:
        raise RuntimeError(f'No data for {symbol} {interval}')
    # yfinance may return MultiIndex columns like ('close', 'SPY'). Flatten to simple names.
    cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            cols.append(c[0])
        else:
            cols.append(c)
    df.columns = cols
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adjclose', 'Volume': 'volume'
    })
    return df

def save_csv(df: pd.DataFrame, path: str):
    df.to_csv(path)
