from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security_headers import add_security_headers


def _app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(add_security_headers)

    @app.get("/probe")
    def probe() -> dict[str, bool]:
        return {"ok": True}

    return app


async def test_security_headers_are_present_on_every_response() -> None:
    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/probe")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "max-age=63072000" in response.headers["strict-transport-security"]


async def test_csp_allow_lists_the_swagger_ui_cdn() -> None:
    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/probe")

    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "cdn.jsdelivr.net" in csp
    assert "frame-ancestors 'none'" in csp
