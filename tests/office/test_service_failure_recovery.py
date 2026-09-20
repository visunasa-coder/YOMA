from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost


def test_failed_start_can_be_recovered():
    class RecoverableRuntime(YomaEmbeddedRuntime):
        def __init__(self):
            super().__init__(collection_interval=3600)
            self.attempts = 0

        def start(self):
            self.attempts += 1
            if self.attempts == 1:
                self._runtime_state = "failed"
                raise RuntimeError("temporary startup failure")
            super().start()

    runtime = RecoverableRuntime()
    host = ServiceHost(runtime)

    try:
        host.start()
    except RuntimeError:
        pass

    assert host.status()["state"] == "failed"

    host.start()

    assert host.running is True
    assert host.status()["state"] == "running"

    host.stop()


def test_recovery_preserves_runtime_instance():
    class RecoverableRuntime(YomaEmbeddedRuntime):
        def __init__(self):
            super().__init__(collection_interval=3600)
            self.attempts = 0

        def start(self):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("temporary failure")
            super().start()

    runtime = RecoverableRuntime()
    host = ServiceHost(runtime)
    original = host.runtime

    try:
        host.start()
    except RuntimeError:
        pass

    host.start()

    assert host.runtime is original

    host.stop()


def test_recovery_restores_healthy_state():
    class RecoverableRuntime(YomaEmbeddedRuntime):
        def __init__(self):
            super().__init__(collection_interval=3600)
            self.attempts = 0

        def start(self):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("temporary failure")
            super().start()

    host = ServiceHost(RecoverableRuntime())

    try:
        host.start()
    except RuntimeError:
        pass

    assert host.health()["healthy"] is False

    host.start()

    assert host.health()["healthy"] is True

    host.stop()


def test_recovery_after_clean_stop():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    host.stop()

    host.start()

    assert host.running is True
    assert host.health()["healthy"] is True

    host.stop()


def test_failed_recovery_remains_failed():
    class AlwaysFailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            self._runtime_state = "failed"
            raise RuntimeError("permanent failure")

    host = ServiceHost(AlwaysFailingRuntime(collection_interval=3600))

    for _ in range(2):
        try:
            host.start()
        except RuntimeError:
            pass

    assert host.running is False
    assert host.status()["state"] == "failed"
    assert host.health()["healthy"] is False


def test_stop_after_failed_recovery_is_safe():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            raise RuntimeError("failure")

    host = ServiceHost(FailingRuntime(collection_interval=3600))

    try:
        host.start()
    except RuntimeError:
        pass

    host.stop()
    host.stop()

    assert host.running is False
    assert host.status()["state"] == "stopped"


def test_recovery_does_not_create_second_runtime():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    host.stop()
    host.start()

    assert host.runtime is runtime

    host.stop()


def test_recovery_lifecycle_is_deterministic():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    host.stop()
    host.start()

    assert host.status()["state"] == "running"
    assert host.status()["runtime_state"] == "running"

    host.stop()

    assert host.status()["state"] == "stopped"
    assert host.status()["runtime_state"] == "stopped"
