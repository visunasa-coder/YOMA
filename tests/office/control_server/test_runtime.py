from unittest.mock import MagicMock, patch

from yoma.office.control_server.windows_service.runtime import ControlServerRuntime


def test_runtime_start_starts_agent_and_server() -> None:
    agent = MagicMock()
    embedded_runtime = MagicMock()
    embedded_runtime.running = False

    runtime = ControlServerRuntime(
        agent=agent,
        embedded_runtime=embedded_runtime,
        port=9876,
    )

    fake_server = MagicMock()
    fake_thread = MagicMock()
    fake_thread.is_alive.return_value = True

    with (
        patch(
            "yoma.office.control_server.windows_service.runtime.uvicorn.Config"
        ),
        patch(
            "yoma.office.control_server.windows_service.runtime.uvicorn.Server",
            return_value=fake_server,
        ),
        patch(
            "yoma.office.control_server.windows_service.runtime.threading.Thread",
            return_value=fake_thread,
        ),
    ):
        runtime.start()

    agent.start.assert_called_once()
    embedded_runtime.start.assert_called_once()

    assert runtime.server is fake_server
    assert runtime.thread is fake_thread
    assert runtime.running is True

    fake_thread.start.assert_called_once()


def test_runtime_start_is_idempotent() -> None:
    agent = MagicMock()
    embedded_runtime = MagicMock()
    embedded_runtime.running = False

    runtime = ControlServerRuntime(
        agent=agent,
        embedded_runtime=embedded_runtime,
    )

    fake_server = MagicMock()
    fake_thread = MagicMock()
    fake_thread.is_alive.return_value = True

    with (
        patch(
            "yoma.office.control_server.windows_service.runtime.uvicorn.Config"
        ),
        patch(
            "yoma.office.control_server.windows_service.runtime.uvicorn.Server",
            return_value=fake_server,
        ),
        patch(
            "yoma.office.control_server.windows_service.runtime.threading.Thread",
            return_value=fake_thread,
        ),
    ):
        runtime.start()
        runtime.start()

    agent.start.assert_called_once()
    embedded_runtime.start.assert_called_once()
    fake_thread.start.assert_called_once()


def test_runtime_stop_stops_server_and_runtime() -> None:
    agent = MagicMock()
    embedded_runtime = MagicMock()
    embedded_runtime.running = True

    runtime = ControlServerRuntime(
        agent=agent,
        embedded_runtime=embedded_runtime,
    )

    fake_server = MagicMock()
    fake_thread = MagicMock()
    fake_thread.is_alive.return_value = True

    runtime.server = fake_server
    runtime.thread = fake_thread

    runtime.stop()

    fake_server.should_exit = True
    fake_thread.join.assert_called_once_with(timeout=10)
    embedded_runtime.stop.assert_called_once()
    agent.stop.assert_called_once()

    assert runtime.server is None
    assert runtime.thread is None


def test_runtime_running_reflects_thread_state() -> None:
    agent = MagicMock()
    embedded_runtime = MagicMock()

    runtime = ControlServerRuntime(
        agent=agent,
        embedded_runtime=embedded_runtime,
    )

    assert runtime.running is False

    fake_thread = MagicMock()
    fake_thread.is_alive.return_value = True

    runtime.thread = fake_thread

    assert runtime.running is True
