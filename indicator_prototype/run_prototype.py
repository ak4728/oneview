import argparse
from data import fetch_ohlcv, save_csv
from indicators import compute_indicators
from train import train_model
from pinegen import generate_pine
from backtest import simple_threshold_backtest
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--symbol', default='SPY')
    p.add_argument('--interval', default='1d')
    p.add_argument('--years', type=int, default=5)
    args = p.parse_args()

    print('Fetching data...')
    df = fetch_ohlcv(args.symbol, interval=args.interval, years=args.years)
    save_csv(df, f'{args.symbol}_{args.interval}.csv')

    print('Computing indicators...')
    df_ind = compute_indicators(df)
    df_ind.to_csv(f'{args.symbol}_{args.interval}_indicators.csv')

    print('Training model...')
    model, importance, shap_values = train_model(df_ind)

    print('Top features:')
    print(importance.head(10))

    # Create a simple weighted combo using top 5 features (normalized weights)
    top = importance.head(5)
    weights = (top / top.sum()).to_dict()
    feature_weights = [(k, float(v)) for k, v in weights.items()]

    # Generate indicator Pine
    pine = generate_pine(feature_weights, title=f'{args.symbol} Auto Combo', as_strategy=False)
    with open('generated_combo.pine', 'w') as f:
        f.write(pine)

    # Generate strategy Pine
    strat_pine = generate_pine(feature_weights, title=f'{args.symbol} Auto Strategy', as_strategy=True)
    with open('generated_strategy.pine', 'w') as f:
        f.write(strat_pine)

    print('Generated Pine scripts: generated_combo.pine and generated_strategy.pine')

    # For local backtest: compute per-feature z-scores same as Pine mapping
    df_test = df_ind.copy()
    norm_len = 20
    for name, weight in feature_weights:
        col = name
        if col in df_test.columns:
            m = df_test[col].rolling(norm_len).mean()
            s = df_test[col].rolling(norm_len).std()
            z = s.replace(0, pd.NA)
            df_test[col + '_z'] = (df_test[col] - m) / s
        else:
            df_test[col + '_z'] = 0

    # build combo column
    combo_raw = sum((weight * df_test[name + '_z'].fillna(0)) for name, weight in feature_weights)
    df_test['combo'] = combo_raw.ewm(span=3).mean()

    # Run a simple backtest using threshold=0
    metrics, trades = simple_threshold_backtest(df_test, combo_col='combo', threshold=0.0)
    print('Backtest metrics:')
    print(metrics)
    trades.to_csv('backtest_trades.csv')
    print('Saved trades to backtest_trades.csv')


if __name__ == '__main__':
    main()
