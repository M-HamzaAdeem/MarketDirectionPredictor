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
tested before wiring in a real feed. Two prediction paths run side by
side: a Phase 3 rule-based direction/confidence score on every candle
close ([docs/prediction-method.md](docs/prediction-method.md)), and an
ICT/Smart Money Concepts signal engine that only ever produces a fully-
specified, risk:reward-gated trade setup — entry/stop/target and full
reasoning, graded to a win/loss/expired outcome once it resolves
([docs/signal-method.md](docs/signal-method.md)).

The dashboard shows live prices, feed status, the open-signal feed (the
main event), and the Phase 3 predictions table — all pushed over
WebSocket. The mock feed runs on an accelerated virtual clock by default
(`MOCK_TIME_ACCELERATION=60` in `backend/.env`), so a 4-hour candle closes
in about 4 real minutes instead of 4 real hours.

A second, fully independent market-data pipeline (own DB tables, own
prediction/signal instances) runs alongside the `FEED_PROVIDER` feed
above, sourced from TradingView's unofficial WebSocket protocol — this is
the dashboard's **default** data source out of the box (`TRADINGVIEW_ENABLED=true`
in `backend/.env`; set to `false` to run `FEED_PROVIDER` only, since it's
an unofficial protocol that can break if TradingView changes it). A
source toggle on the dashboard switches which pipeline's data is
displayed; both keep running regardless of which is selected. See
`app/services/tradingview_feed_service.py`.

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

## Running as Windows Services (no PowerShell window needed)

`scripts/windows-service/install-services.ps1` wraps both dev servers
(`uvicorn --reload`, `npm run dev`) as Windows Services via [NSSM](https://nssm.cc)
— they survive reboot, auto-restart on crash, and run headless. From an
**elevated** PowerShell:

```powershell
cd D:\path\to\MarketDirectionPredictor
.\scripts\windows-service\install-services.ps1
```

Stops any manually-started dev servers first (they'd otherwise fight the
services for ports 8000/5173), installs NSSM via Chocolatey if it isn't
already present, then creates and starts `MarketPredictorBackend` and
`MarketPredictorFrontend`. Logs land in `logs/`. Manage with
`nssm status|restart|stop <name>`; remove both with
`.\scripts\windows-service\uninstall-services.ps1` (also elevated).

## Project layout

```
backend/   FastAPI app — feeds, storage, features, prediction, services, api
frontend/  React + Vite + TS + Tailwind dashboard
docs/      Architecture and design notes
```

See [docs/architecture.md](docs/architecture.md) for the full design and
phase plan.
