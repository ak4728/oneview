from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import traceback
import os

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/ohlcv")
def get_ohlcv():
    symbol   = request.args.get("symbol", "BTC-USD").upper()
    interval = request.args.get("interval", "5m")  # 1m 5m 15m 30m

    # 1m data max = last 7 days on Yahoo Finance
    period = "7d"

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            return jsonify({"error": f"No data found for '{symbol}'. Try: BTC-USD, AAPL, EURUSD=X"}), 404

        # Ensure index is datetime and strip timezone for clean JSON
        try:
            df.index = pd.to_datetime(df.index)
            if getattr(df.index, 'tz', None) is not None:
                try:
                    # convert to UTC then remove tz info (works for tz-aware index)
                    df.index = df.index.tz_convert('UTC').tz_localize(None)
                except Exception:
                    try:
                        df.index = df.index.tz_localize(None)
                    except Exception:
                        pass
        except Exception:
            # if any conversion fails, fall back to leaving the index as-is
            pass
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
