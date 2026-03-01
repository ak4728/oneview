# OneView — Live Intraday (yfinance + Flask)

## Quick Start (Local)
```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows PowerShell
pip install -r requirements.txt
python app.py
# Open http://localhost:5000 in your browser
```

## Deploy (Render)
1. Push this folder to a GitHub repo.
2. Create a new Web Service on render.com and point it to the repo.
3. Render will detect `render.yaml` and build the service.

> Note: Free Render instances sleep after inactivity. First request after idle can take ~30s.

## Supported Symbols
- Crypto: `BTC-USD`, `ETH-USD`, etc.
- Stocks: `AAPL`, `TSLA`, `NVDA`, etc.
- Forex: `EURUSD=X`, `GBPUSD=X`, etc.

## API
GET /api/ohlcv?symbol=BTC-USD&interval=5m

- `symbol` — Yahoo Finance ticker (default: `BTC-USD`)
- `interval` — `1m` | `5m` | `15m` | `30m` (default: `5m`)
- The API returns the most recent data (1m data is limited to ~7 days by Yahoo)

## Notes
- The web UI (`index.html`) renders signals (BUY/SELL) aligned to candle indices. A previous issue where arrows clustered at the left edge was fixed by aligning signal datasets to the chart's category labels.
- Timestamp values come from Yahoo Finance and may reflect exchange timezones (stocks) or UTC (crypto). The UI displays the timestamps received from the API.

If you want, I can also update the README with deployment example commands or add a short troubleshooting section.
