import streamlit as st
import pandas as pd
from data import fetch_ohlcv
from indicators import compute_indicators
from train import train_model
from pinegen import generate_pine
from backtest import simple_threshold_backtest
import plotly.express as px


st.title('Indicator Prototype Explorer')

symbol = st.sidebar.text_input('Symbol', 'SPY')
years = st.sidebar.number_input('Years', 1, 10, 5)
if st.sidebar.button('Load Data'):
    with st.spinner('Fetching data...'):
        df = fetch_ohlcv(symbol, years=years)
        df_ind = compute_indicators(df)
        st.session_state['df_ind'] = df_ind
        st.success('Data loaded')

if 'df_ind' in st.session_state:
    df_ind = st.session_state['df_ind']
    st.subheader('Indicator Sample')
    st.dataframe(df_ind.tail(50))

    if st.button('Train & Generate'):
        with st.spinner('Training model...'):
            model, importance, shap_values = train_model(df_ind)
            st.write('Top features')
            st.write(importance.head(10))
            top = importance.head(5)
            weights = (top / top.sum()).to_dict()
            feature_weights = [(k, float(v)) for k, v in weights.items()]
            pine = generate_pine(feature_weights, title=f'{symbol} Auto Combo', as_strategy=False)
            st.subheader('Generated Pine Script (indicator)')
            st.code(pine)
            strat = generate_pine(feature_weights, title=f'{symbol} Auto Strategy', as_strategy=True)
            st.subheader('Generated Pine Script (strategy)')
            st.code(strat)
            # compute combo locally
            df_test = df_ind.copy()
            norm_len = 20
            for name, weight in feature_weights:
                if name in df_test.columns:
                    m = df_test[name].rolling(norm_len).mean()
                    s = df_test[name].rolling(norm_len).std()
                    df_test[name + '_z'] = (df_test[name] - m) / s
                else:
                    df_test[name + '_z'] = 0
            combo_raw = sum((weight * df_test[name + '_z'].fillna(0)) for name, weight in feature_weights)
            df_test['combo'] = combo_raw.ewm(span=3).mean()
            metrics, trades = simple_threshold_backtest(df_test, combo_col='combo', threshold=0.0)
            st.subheader('Backtest Metrics')
            st.json(metrics)
            st.subheader('Equity Curve')
            cum = (1 + trades['returns']).cumprod()
            fig = px.line(cum, title='Equity Curve')
            st.plotly_chart(fig)
