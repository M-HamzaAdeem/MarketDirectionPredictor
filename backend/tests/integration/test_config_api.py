from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers import config


async def test_get_config_returns_the_effective_settings_and_strategy_parameters() -> None:
    app = FastAPI()
    app.include_router(config.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/config")

    assert response.status_code == 200
    body = response.json()

    assert body["feed_provider"] == "mock"
    assert body["mock_time_acceleration"] == 60.0
    assert set(body["symbols"]) == {"XAUUSD", "EURUSD", "AUDUSD"}
    assert set(body["timeframes"]) == {"1m", "5m", "15m", "1h", "4h"}
    assert body["min_risk_reward"] == 1.8
    assert body["ote_shallow_ratio"] == 0.705
    assert body["ote_deep_ratio"] == 0.79
    assert body["stop_atr_buffer_multiplier"] == 0.25
    assert body["impulse_atr_multiplier"] == 1.5
    assert body["signal_expiry_days"] == 5.0
    assert body["rsi_bullish_threshold"] == 60.0
    assert body["rsi_bearish_threshold"] == 40.0
    assert body["sma_fast_period"] == 10
    assert body["sma_slow_period"] == 30
    assert body["rsi_period"] == 14
    assert body["atr_period"] == 14
    assert body["momentum_period"] == 10
    assert body["volatility_period"] == 20
