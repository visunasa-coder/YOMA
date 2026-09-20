from __future__ import annotations

from unittest.mock import MagicMock, patch

from yoma.office.control_server.windows_service.service import (
    YomaWindowsService,
)


def _fake_init(self, args) -> None:
    self.runtime = MagicMock()
    self.stop_event = MagicMock()
    self.worker_thread = None


def test_service_metadata() -> None:
    assert YomaWindowsService._svc_name_ == "YomaControlServer"
    assert YomaWindowsService._svc_display_name_ == "YOMA Control Server"


def test_service_stop_stops_runtime() -> None:
    with patch.object(
        YomaWindowsService,
        "__init__",
        _fake_init,
    ):
        service = YomaWindowsService(None)

        with (
            patch.object(service, "ReportServiceStatus"),
            patch(
                "yoma.office.control_server.windows_service.service.win32event.SetEvent"
            ) as set_event,
        ):
            service.SvcStop()

        set_event.assert_called_once_with(service.stop_event)
        service.runtime.stop.assert_called_once()


def test_service_start_starts_runtime() -> None:
    with patch.object(
        YomaWindowsService,
        "__init__",
        _fake_init,
    ):
        service = YomaWindowsService(None)

        with patch.object(service, "ReportServiceStatus"):
            with patch.object(
                service,
                "_run_loop",
                return_value=None,
            ):
                service.SvcDoRun()

        service.runtime.start.assert_called_once()
        assert service.worker_thread is not None
