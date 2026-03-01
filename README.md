# SuperTrend — Intraday (yfinance + Flask + Render)

## Local Development
```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

## Deploy to Render (Free)

1. Push this entire folder to a **GitHub repo** (public or private)
2. Go to [render.com](https://render.com) → Sign up / Log in
3. Click **"New +"** → **"Web Service"**
4. Connect your GitHub repo
5. Render auto-detects `render.yaml` — just click **"Create Web Service"**
6. Wait ~2 min for the build to finish
7. Your live URL will be: `https://supertrend-api.onrender.com` (or similar)

> ⚠️ **Free tier note**: The service spins down after 15 min of inactivity.
> First request after idle takes ~30 seconds to wake up. Subsequent requests are fast.

## Supported Symbols
- **Crypto**: BTC-USD, ETH-USD, SOL-USD, etc.
- **Stocks**: AAPL, TSLA, NVDA, SPY, etc.
- **Forex**: EURUSD=X, GBPUSD=X, JPYUSD=X, etc.

## API Endpoints
```
GET /api/ohlcv?symbol=BTC-USD&interval=5m
```
- `symbol` — Yahoo Finance ticker (default: BTC-USD)
- `interval` — 1m | 5m | 15m | 30m (default: 5m)
- Always returns last 7 days of data (1m data limited to 7 days by Yahoo)
