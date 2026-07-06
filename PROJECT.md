\# Market Direction Predictor



\## Goal



Build a complete full-stack market direction prediction application for:



\- XAUUSD

\- EURUSD

\- AUDUSD



The application should fetch live market data from a websocket/data feed, process candles/ticks, calculate indicators and market structure, predict short-term market direction, and display results in a clean dashboard.



\## Application Type



Preferred application type: Web App.



The project should include both:



\- Backend

\- Frontend



A WPF desktop app can be considered later, but the first version should be a full-stack web application because it is better suited for dashboards, charts, live updates, and future mobile/browser access.



\## Important Note About TradingView



TradingView does not provide a simple official public websocket API for automated data extraction like brokers or exchanges do. If TradingView access is unreliable or against terms, the project should support fallback providers.



The data feed layer must be modular so that TradingView can be replaced with another provider without changing the rest of the system.



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



For each symbol and timeframe, show:



\- Symbol

\- Timeframe

\- Current price

\- Direction: bullish / bearish / neutral

\- Confidence percentage

\- Reason summary

\- Timestamp

\- Latest candle data

\- Recent prediction history



\## Core Features



The application should include:



1\. Live market data feed

2\. Candle/tick storage

3\. Indicator calculation

4\. Market structure detection

5\. Prediction engine

6\. Prediction logging

7\. Backtesting support later

8\. Dashboard frontend

9\. Backend API

10\. Backend-to-frontend websocket updates

11\. Configuration system

12\. Error logging

13\. Safe fallback if live feed is unavailable



\## Dashboard Requirements



The frontend dashboard should show:



\- Live price cards for XAUUSD, EURUSD, and AUDUSD

\- Direction signal: bullish / bearish / neutral

\- Confidence percentage

\- Reason summary

\- Last updated time

\- Chart area for each symbol

\- Timeframe selector

\- Prediction history table

\- Feed connection status

\- Model status

\- Basic settings page later



\## Suggested Features for Prediction



Use a combination of:



\- Trend direction

\- Market structure

\- Break of structure

\- Moving averages

\- RSI

\- ATR

\- Candle momentum

\- Volatility

\- Session timing

\- News filter later



\## Preferred Tech Stack



Backend:



\- Python 3.11+

\- FastAPI

\- WebSocket support

\- Pandas or Polars

\- SQLite for first version

\- SQLAlchemy

\- Scikit-learn or XGBoost for first ML model

\- Pydantic for schemas

\- APScheduler or background tasks for polling/processing if needed



Frontend:



\- React

\- Vite

\- TypeScript

\- Tailwind CSS

\- Chart library for market charts

\- WebSocket client for live prediction updates



Project:



\- Monorepo structure

\- Backend and frontend inside same repository

\- Clear README

\- .env.example

\- Modular feed adapters

\- No auto-trading in version 1



\## Safety Rules



\- No auto trading in version 1

\- No real-money execution

\- Do not connect to broker execution API in first version

\- Log every prediction

\- Backtest before trusting signals

\- Clearly show uncertainty

\- Never present predictions as guaranteed

\- Show disclaimer in dashboard



\## Suggested Project Structure



```text

backend/

&#x20; app/

&#x20;   api/

&#x20;   core/

&#x20;   feeds/

&#x20;   storage/

&#x20;   features/

&#x20;   prediction/

&#x20;   services/

&#x20;   schemas/

&#x20;   utils/

&#x20; tests/

&#x20; requirements.txt

&#x20; .env.example



frontend/

&#x20; src/

&#x20;   components/

&#x20;   pages/

&#x20;   services/

&#x20;   hooks/

&#x20;   types/

&#x20;   utils/

&#x20; package.json

&#x20; vite.config.ts

&#x20; tailwind.config.js



docs/

&#x20; architecture.md

&#x20; data-feed-notes.md

&#x20; prediction-method.md



README.md

PROJECT.md

.gitignore

