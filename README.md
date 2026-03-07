# OneView — Live Intraday (Flask + Node API)

<img width="1886" height="891" alt="image" src="https://github.com/user-attachments/assets/c3827e1e-1877-4780-bb0d-0c04e2c27688" />


## Quick Start (Flask)
```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows PowerShell
pip install -r requirements.txt
python app.py
# Open http://localhost:5000 in your browser
```

The Flask app serves:
- `/` -> `index.html`
- `/styles.css` -> `styles.css`
- `/main.js` -> `main.js`

## Node Server (server/)

The repository includes a small Node/TypeScript API server located in the `server/` folder. To run the development server (uses `ts-node-dev`):

```bash
# from the repo root
npm --prefix server install
npm --prefix server run dev
```

Stop the server with Ctrl+C in the terminal where it's running. If the server was started in another terminal, stop that terminal first before starting a new instance to avoid port conflicts (the server listens on port 4000 by default).

The Node server also serves static files from the repo root, so the split frontend (`index.html`, `styles.css`, `main.js`) works at `http://localhost:4000`.

## Frontend Features

The UI is now split into separate files for easier maintenance:
- `index.html` (structure)
- `styles.css` (styling)
- `main.js` (logic)

### Usability Improvements
- Indicator help tooltips with plain-language examples (ATR period, multiplier, ATR method, confirm bars).
- Grouped controls with a dedicated **Filters** section.
- Range filter options: `All`, `Last Day`, and `Last 24 Hours`.
- Right-side quick ticker panel (click ticker to fetch + run immediately).
- Custom favorites with add/remove support.
- Persistent user preferences (symbol, interval, filters, indicator settings, toggles) via local storage.
- Updated typography for easier reading.

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
- `interval` — `1m` | `5m` | `15m` | `30m` | `1d` (default: `5m`)
- The API returns the most recent data (1m data is limited to ~7 days by Yahoo)

## Notes
- The web UI (`index.html`) renders signals (BUY/SELL) aligned to candle indices. A previous issue where arrows clustered at the left edge was fixed by aligning signal datasets to the chart's category labels.
- Timestamp values come from Yahoo Finance and may reflect exchange timezones (stocks) or UTC (crypto). The UI displays the timestamps received from the API.

## Troubleshooting

- If port `4000` is in use, stop the process using it before starting the Node server.
- If the page loads without styles or scripts, verify `styles.css` and `main.js` are reachable from your chosen server.
- If no candles appear after filtering, switch range to `All` and try again.
