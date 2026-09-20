import sys
import servicemanager
import win32serviceutil

from yoma.office.control_server.windows_service.service import YomaWindowsService

if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(YomaWindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(YomaWindowsService)
