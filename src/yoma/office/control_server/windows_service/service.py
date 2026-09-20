from __future__ import annotations

import threading
import time

import win32event
import win32service
import win32serviceutil


class YomaWindowsService(win32serviceutil.ServiceFramework):
    """Windows Service wrapper for the YOMA Control Server runtime."""

    _svc_name_ = "YomaControlServer"
    _svc_display_name_ = "YOMA Control Server"
    _svc_description_ = (
        "Runs the YOMA Office Management Control Server in the background."
    )

    def __init__(self, args) -> None:
        super().__init__(args)

        # Keep the SCM bootstrap path free of YOMA imports and initialization.
        # The runtime is created only after StartServiceCtrlDispatcher has
        # connected this process to the Service Control Manager.
        self.runtime = None
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.worker_thread: threading.Thread | None = None

    def SvcStop(self) -> None:
        """Handle a Windows service stop request."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        win32event.SetEvent(self.stop_event)

        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)

        if self.runtime is not None:
            self.runtime.stop()

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self) -> None:
        """Handle the Windows service start request."""
        from yoma.office.control_server.windows_service.runtime import (
            ControlServerRuntime,
        )

        # Allow a runtime supplied by an integration harness while keeping
        # the normal service bootstrap lazy and import-light.
        if self.runtime is None:
            self.runtime = ControlServerRuntime()
        self.runtime.start()

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        self.worker_thread = threading.Thread(
            target=self._run_loop,
            name="yoma-control-server-service",
            daemon=True,
        )
        self.worker_thread.start()

        self.worker_thread.join()

    def _run_loop(self) -> None:
        """Keep the service alive until Windows requests shutdown."""
        while True:
            result = win32event.WaitForSingleObject(
                self.stop_event,
                1000,
            )

            if result == win32event.WAIT_OBJECT_0:
                break

            time.sleep(0.1)


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(YomaWindowsService)
