# Market Direction Predictor

A full-stack dashboard that predicts short-term market direction (bullish /
bearish / neutral, with a confidence score and reasoning) for XAUUSD, EURUSD,
and AUDUSD across 1m/5m/15m timeframes.

> **This tool predicts direction only. It never places trades.** No
> auto-trading, no broker execution, no real-money integration exists in
> this version. Predictions are probabilistic estimates, not financial
> advice. See [PROJECT.md](PROJECT.md) and [docs/architecture.md](docs/architecture.md).

Version 1 runs on synthetic (mock) market data so the full pipeline —
feed → candles → indicators → prediction → dashboard — can be built and
tested before wiring in a real feed.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, WebSockets
- **Frontend:** React, Vite, TypeScript, Tailwind CSS

## Backend — run locally

```powershell
cd backend
py -m venv .venv
./.venv/Scripts/pip install -r requirements.txt
Copy-Item .env.example .env
./.venv/Scripts/uvicorn app.main:app --reload
```

The API serves at `http://localhost:8000`; check `http://localhost:8000/health`.

## Frontend — run locally

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The dashboard serves at `http://localhost:5173`.

## Project layout

```
backend/   FastAPI app — feeds, storage, features, prediction, services, api
frontend/  React + Vite + TS + Tailwind dashboard
docs/      Architecture and design notes
```

See [docs/architecture.md](docs/architecture.md) for the full design and
phase plan.
