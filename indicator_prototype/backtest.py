import pandas as pd
import numpy as np

def simple_threshold_backtest(df: pd.DataFrame, combo_col: str = 'combo', threshold: float = 0.0):
    """Run a simple backtest: go long when combo > threshold, flat otherwise.
    Assumes df has `close` and `combo` columns aligned by index.
    Returns a dict of basic metrics and a trades DataFrame.
    """
    prices = df['close'].astype(float)
    signal = df[combo_col] > threshold

    # positions (1 if long, 0 if flat)
    pos = signal.astype(int).shift(1).fillna(0)
    returns = prices.pct_change().fillna(0)
    strat_ret = returns * pos

    cum_ret = (1 + strat_ret).cumprod()
    total_return = cum_ret.iloc[-1] - 1

    days = (df.index[-1] - df.index[0]).days if hasattr(df.index, 'tz') or hasattr(df.index, 'tzinfo') else len(df)
    years = max(days / 365.25, 1/252)
    cagr = (1 + total_return) ** (1 / years) - 1

    # max drawdown
    running_max = cum_ret.cummax()
    drawdown = cum_ret / running_max - 1
    max_dd = drawdown.min()

    metrics = {
        'total_return': float(total_return),
        'cagr': float(cagr),
        'max_drawdown': float(max_dd),
    }

    trades = pd.DataFrame({'price': prices, 'signal': signal, 'position': pos, 'returns': strat_ret})
    return metrics, trades
