from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)


def main() -> None:
    runtime = ControlServerRuntime(
        host="127.0.0.1",
        port=8766,
    )

    try:
        runtime.start()

        print("YOMA Control Server running")
        print("API: http://127.0.0.1:8766")
        print("Press Ctrl+C to stop.")

        if runtime.thread:
            runtime.thread.join()

    except KeyboardInterrupt:
        print("\nStopping YOMA Control Server...")

    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
