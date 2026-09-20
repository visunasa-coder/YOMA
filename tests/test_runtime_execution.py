from yoma.runtime import YomaRuntime


def test_runtime_can_execute_injected_task():
    calls = []

    def executor(task):
        calls.append(task)
        return {"status": "completed", "task": task}

    runtime = YomaRuntime(mode="embedded", executor=executor)

    runtime.start()

    result = runtime.execute("hello")

    assert result == {"status": "completed", "task": "hello"}
    assert calls == ["hello"]

    runtime.stop()
