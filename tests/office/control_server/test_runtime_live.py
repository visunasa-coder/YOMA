from __future__ import annotations

import time

import httpx

from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)


def _wait_for_api(
    url: str,
    timeout: float = 10.0,
) -> httpx.Response:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                return response
        except httpx.HTTPError:
            pass

        time.sleep(0.1)

    raise AssertionError(f"YOMA API did not become ready: {url}")


def test_runtime_serves_real_api_and_stops() -> None:
    runtime = ControlServerRuntime(
        host="127.0.0.1",
        port=18766,
    )

    try:
        runtime.start()

        response = _wait_for_api(
            "http://127.0.0.1:18766/health"
        )

        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "ok"
        assert data["service"] == "yoma-control-server"
        assert data["running"] is True

        status = httpx.get(
            "http://127.0.0.1:18766/status",
            timeout=2.0,
        )

        assert status.status_code == 200
        assert status.json()["running"] is True

    finally:
        runtime.stop()

    assert runtime.running is False
