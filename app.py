from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import traceback
import os

app = Flask(__name__, static_folder="main")
CORS(app)

@app.route("/")
def index():
    return send_from_directory("", "index.html")

@app.route("/styles.css")
def styles():
    return send_from_directory("", "styles.css")

@app.route("/main.js")
def script_main():
    return send_from_directory("", "main.js")

@app.route("/api/ohlcv")
def get_ohlcv():
    symbol   = request.args.get("symbol", "BTC-USD").upper()
    interval = request.args.get("interval", "5m")  # 1m 5m 15m 30m

    # OneView v1.4.0 — 1m data max = last 7 days on Yahoo Finance
    period = "7d"

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            return jsonify({"error": f"No data found for '{symbol}'. Try: BTC-USD, AAPL, EURUSD=X"}), 404

        # Strip timezone for clean JSON
        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        df.reset_index(inplace=True)

        date_col = "Datetime" if "Datetime" in df.columns else "Date"

        records = []
        for _, row in df.iterrows():
            records.append({
                "date":   str(row[date_col])[:16],   # "2024-01-01 09:30"
                "open":   round(float(row["Open"]),  4),
                "high":   round(float(row["High"]),  4),
                "low":    round(float(row["Low"]),   4),
                "close":  round(float(row["Close"]), 4),
                "volume": int(row.get("Volume", 0) or 0),
            })

        return jsonify({
            "symbol":   symbol,
            "interval": interval,
            "count":    len(records),
            "data":     records,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)