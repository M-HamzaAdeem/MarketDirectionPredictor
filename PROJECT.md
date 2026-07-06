\# Market Direction Predictor



\## Goal



Build a local market direction prediction system for:



\- XAUUSD

\- EURUSD

\- AUDUSD



The system should fetch live market data from a websocket/data feed, process candles/ticks, calculate indicators and market structure, and predict short-term market direction.



\## Important Note



TradingView does not provide a simple official public websocket API for automated data extraction like brokers or exchanges do. If TradingView access is unreliable or against terms, the project should support fallback providers.



\## First Version Scope



Version 1 should only predict market direction.



It should not place trades automatically.



\## Symbols



\- XAUUSD

\- EURUSD

\- AUDUSD



\## Timeframes



\- 1m

\- 5m

\- 15m



\## Prediction Output



For each symbol, output:



\- Symbol

\- Timeframe

\- Current price

\- Direction: bullish / bearish / neutral

\- Confidence percentage

\- Reason summary

\- Timestamp



\## Suggested Features



Use a combination of:



\- Trend direction

\- Market structure

\- Break of structure

\- Moving averages

\- RSI

\- ATR

\- Candle momentum

\- Session timing

\- News filter later



\## Preferred Tech Stack



\- Python 3.11+

\- FastAPI later for API

\- WebSocket client for live data

\- Pandas or Polars for data processing

\- SQLite for local storage

\- Scikit-learn or XGBoost for first ML model

\- Simple CLI first

\- Dashboard later



\## Safety Rules



\- No auto trading in version 1

\- No real-money execution

\- Log every prediction

\- Backtest before trusting signals

\- Clearly show uncertainty

