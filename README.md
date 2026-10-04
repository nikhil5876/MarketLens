# MarketLens — Angel One charts

Python FastAPI backend with a responsive, dependency-free web frontend. Includes six NSE stocks, OHLC candlestick/line charts, volume, interval selection, hover inspection and a watchlist. The web preview uses sample data. Run locally for Angel One data.

## Run on your Mac

Use Python 3.11 or 3.12. Open Terminal inside the extracted folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. It starts in demo mode.

## Connect Angel One

Edit `.env`: set `MARKET_MODE=live`, then fill in your SmartAPI API key, Angel One client code, account PIN, and authenticator TOTP **secret** (not the changing six-digit code). Keep this file private. Restart the server. No credentials are entered into the browser. Session login happens on first data request and is refreshed on a new IST day; rejected API sessions are reset for the next request.

Quotes are polled every five seconds in one batch; candle history refreshes every thirty seconds. This is REST polling, not tick-by-tick streaming. Latest prices and candle history can differ because candle endpoints have their own availability/latency. Market holidays and closed sessions may show the last available data. The quote timestamp is the local fetch time, not the exchange tick timestamp.

Stock tokens are a small built-in NSE watchlist. Check Angel One's instrument master if a security's token changes. To add instruments, update STOCKS in backend/app.py and the frontend list in dist/app.js together. Historical data uses actual market sessions; sample data does not model holidays or trading hours.

API routes: GET /api/status, /api/quotes, /api/candles?symbol=RELIANCE&interval=5m. Supported intervals: 1m, 5m, 15m, 1h, 1d.

Run one worker bound to localhost: this is a personal application without user authentication. For an internet deployment of the Python backend, add authentication, HTTPS and access restrictions first. Never commit `.env`. The static hosted preview does not run Python or connect your broker. No order placement is included.

## Verification

Demo endpoints and frontend JavaScript were checked. Live broker requests require your credentials and were not tested against an account. SDK reference: https://github.com/angel-one/smartapi-python
