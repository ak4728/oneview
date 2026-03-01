import traceback

def run():
    try:
        print('Importing modules...')
        from data import fetch_ohlcv
        from indicators import compute_indicators
        from train import train_model
        print('Modules imported')

        print('Fetching data...')
        df = fetch_ohlcv('SPY', interval='1d', years=1)
        print('Data fetched rows=', len(df))

        print('Computing indicators...')
        df_ind = compute_indicators(df)
        print('Indicators computed rows=', len(df_ind))

        print('Training model...')
        model, importance, shap_values = train_model(df_ind)
        print('Model trained; top features:\n', importance.head(5))

    except Exception as e:
        print('Error during run:')
        traceback.print_exc()

if __name__ == '__main__':
    run()
