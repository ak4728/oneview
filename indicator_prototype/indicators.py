import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    # Ensure required columns and numeric types
    data = data.rename(columns={
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
    })
    data['Close'] = pd.to_numeric(data['Close'], errors='coerce')
    data['High'] = pd.to_numeric(data.get('High'), errors='coerce')
    data['Low'] = pd.to_numeric(data.get('Low'), errors='coerce')
    data['Volume'] = pd.to_numeric(data.get('Volume'), errors='coerce')

    # Moving averages
    data['SMA_20'] = _safe_call(ta.sma, data['Close'], length=20)
    data['EMA_20'] = _safe_call(ta.ema, data['Close'], length=20)
    data['EMA_50'] = _safe_call(ta.ema, data['Close'], length=50)

    # Momentum
    data['RSI_14'] = _safe_call(ta.rsi, data['Close'], length=14)
    data['ROC_10'] = _safe_call(ta.roc, data['Close'], length=10)

    # MACD (handle pandas_ta returning None)
    macd = _safe_call(ta.macd, data['Close'])
    if macd is not None and hasattr(macd, 'columns'):
        # prefer known column names, but be defensive
        if 'MACD_12_26_9' in macd.columns:
            data['MACD'] = macd['MACD_12_26_9']
        else:
            # try first column
            data['MACD'] = macd.iloc[:, 0]

        if 'MACDs_12_26_9' in macd.columns:
            data['MACD_SIG'] = macd['MACDs_12_26_9']
        elif macd.shape[1] > 1:
            data['MACD_SIG'] = macd.iloc[:, 1]
        else:
            data['MACD_SIG'] = pd.NA
    else:
        data['MACD'] = pd.NA
        data['MACD_SIG'] = pd.NA

    # Volatility / Bollinger Bands
    bb = _safe_call(ta.bbands, data['Close'], length=20)
    if bb is not None and hasattr(bb, 'columns'):
        # attempt to find expected columns
        for col in ['BBL_20_2.0', 'BBU_20_2.0', 'BBM_20_2.0']:
            if col in bb.columns:
                data[col] = bb[col]
        # also provide common names
        if 'BBL_20_2.0' in bb.columns:
            data['BBL_20'] = bb['BBL_20_2.0']
        if 'BBU_20_2.0' in bb.columns:
            data['BBU_20'] = bb['BBU_20_2.0']
        if 'BBM_20_2.0' in bb.columns:
            data['BBM_20'] = bb['BBM_20_2.0']
    else:
        data['BBL_20'] = pd.NA
        data['BBU_20'] = pd.NA
        data['BBM_20'] = pd.NA

    data['ATR_14'] = _safe_call(ta.atr, data['High'], data['Low'], data['Close'], length=14)

    # Volume-based
    data['OBV'] = _safe_call(ta.obv, data['Close'], data['Volume'])

    # Others
    adx = _safe_call(ta.adx, data['High'], data['Low'], data['Close'], length=14)
    if adx is not None and hasattr(adx, 'columns') and 'ADX_14' in adx.columns:
        data['ADX_14'] = adx['ADX_14']
    else:
        data['ADX_14'] = pd.NA

    data['CCI_20'] = _safe_call(ta.cci, data['High'], data['Low'], data['Close'], length=20)

    # Supertrend (added): default params match the TradingView script
    try:
        st = compute_supertrend(data.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        }), period=10, multiplier=3.0, change_atr=True)
        # merge supertrend columns (they use lowercase names)
        for k, v in st.items():
            data[k] = v
    except Exception:
        # if computation fails, create empty columns
        data['ST_up'] = pd.NA
        data['ST_dn'] = pd.NA
        data['ST_trend'] = pd.NA
        data['ST_buy'] = pd.NA
        data['ST_sell'] = pd.NA

    # Drop rows with NA in essential columns (Close and a few indicators)
    # Keep only rows where Close is present
    data = data.dropna(subset=['Close'])

    # It's okay if some indicator columns are NA; downstream code drops NA as needed
    data = data.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
    })
    return data


def compute_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0, change_atr: bool = True) -> Dict[str, pd.Series]:
    """Compute Supertrend indicator and buy/sell signals.

    Returns a dict of series: ST_up, ST_dn, ST_trend, ST_buy, ST_sell.
    Input `df` expects columns: 'open','high','low','close' (lowercase).
    """
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)

    # Source is hl2 (average of high and low)
    src = (high + low) / 2.0

    # ATR calculation: either built-in ATR or SMA of True Range
    try:
        atr_builtin = ta.atr(high, low, close, length=period)
    except Exception:
        atr_builtin = None

    # compute true range manually (always available) and fallback ATR using rolling mean
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    fallback_atr = tr.rolling(period, min_periods=1).mean()

    if change_atr and atr_builtin is not None:
        atr = atr_builtin
    else:
        atr = fallback_atr

    n = len(df)
    up = np.full(n, np.nan)
    dn = np.full(n, np.nan)
    trend = np.full(n, np.nan)

    up_vals = src - (multiplier * atr)
    dn_vals = src + (multiplier * atr)

    for i in range(n):
        if i == 0:
            up[i] = up_vals.iat[0] if hasattr(up_vals, 'iat') else up_vals.iloc[0]
            dn[i] = dn_vals.iat[0] if hasattr(dn_vals, 'iat') else dn_vals.iloc[0]
            trend[i] = 1
            continue

        prev = i - 1
        up_i = up_vals.iat[i] if hasattr(up_vals, 'iat') else up_vals.iloc[i]
        dn_i = dn_vals.iat[i] if hasattr(dn_vals, 'iat') else dn_vals.iloc[i]

        up_prev = up[prev]
        dn_prev = dn[prev]

        # up := close[1] > up1 ? max(up,up1) : up
        if close.iat[prev] > up_prev:
            up[i] = max(up_i, up_prev)
        else:
            up[i] = up_i

        # dn := close[1] < dn1 ? min(dn,dn1) : dn
        if close.iat[prev] < dn_prev:
            dn[i] = min(dn_i, dn_prev)
        else:
            dn[i] = dn_i

        # trend logic
        prev_trend = trend[prev]
        if prev_trend == -1 and close.iat[i] > dn_prev:
            trend[i] = 1
        elif prev_trend == 1 and close.iat[i] < up_prev:
            trend[i] = -1
        else:
            trend[i] = prev_trend

    st_up = pd.Series(up, index=df.index)
    st_dn = pd.Series(dn, index=df.index)
    st_trend = pd.Series(trend, index=df.index)

    # buy/sell signals
    st_buy = (st_trend == 1) & (st_trend.shift(1) == -1)
    st_sell = (st_trend == -1) & (st_trend.shift(1) == 1)

    return {
        'ST_up': st_up,
        'ST_dn': st_dn,
        'ST_trend': st_trend,
        'ST_buy': st_buy,
        'ST_sell': st_sell,
    }
