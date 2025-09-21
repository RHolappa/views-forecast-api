import asyncio

from starlette.testclient import TestClient

from app.main import app, lifespan


def test_global_exception_handler():
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/boom")
    async def boom():  # type: ignore
        raise RuntimeError("Boom")

    try:
        response = client.get("/boom")
        assert response.status_code == 500
        payload = response.json()
        assert payload["error"] == "Internal server error"
    finally:
        app.router.routes = [
            route for route in app.router.routes if getattr(route, "path", None) != "/boom"
        ]


def test_lifespan_logs(caplog):
    async def run_lifespan():
        async with lifespan(app):
            pass

    caplog.set_level("INFO")
    asyncio.run(run_lifespan())
    assert any("Starting" in record.message for record in caplog.records)
