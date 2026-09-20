from yoma.runtime import YomaRuntime

def main():
    runtime = YomaRuntime(mode="embedded")

    print("Initial:", runtime.status())

    runtime.start()
    print("Running:", runtime.status())

    assert runtime.running is True

    runtime.stop()
    print("Stopped:", runtime.status())

    assert runtime.running is False

    print("EMBEDDED RUNTIME SMOKE TEST: PASS")

if __name__ == "__main__":
    main()
