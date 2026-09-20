from yoma.office.runtime_failure_isolation import RuntimeFailureIsolation


def assess(**overrides):
    values = {
        "components": ("runtime", "event_bus", "intelligence"),
    }
    values.update(overrides)
    return RuntimeFailureIsolation().assess(**values)


def test_healthy_runtime_is_isolated():
    result = assess()
    assert result.isolated is True
    assert result.total_components == 3
    assert result.failed_components == ()


def test_failed_component_is_identified():
    result = assess(failed_components=("event_bus",))
    assert result.failed_components == ("event_bus",)


def test_healthy_components_are_preserved():
    result = assess(failed_components=("event_bus",))
    assert result.healthy_components == ("runtime", "intelligence")


def test_failure_does_not_mark_other_components_failed():
    result = assess(failed_components=("event_bus",))
    assert "runtime" in result.healthy_components
    assert "intelligence" in result.healthy_components


def test_unknown_failed_component_is_ignored():
    result = assess(failed_components=("unknown",))
    assert result.failed_components == ()
    assert result.healthy_components == (
        "runtime",
        "event_bus",
        "intelligence",
    )


def test_duplicate_components_are_deterministic():
    result = assess(
        components=("runtime", "runtime", "event_bus"),
    )
    assert result.total_components == 2


def test_duplicate_failures_are_deduplicated():
    result = assess(
        failed_components=("event_bus", "event_bus"),
        failures=("failure", "failure"),
    )
    assert result.failed_components == ("event_bus",)
    assert result.failures == ("failure",)


def test_failure_messages_are_preserved():
    result = assess(
        failed_components=("event_bus",),
        failures=("event bus unavailable",),
    )
    assert result.failures == ("event bus unavailable",)


def test_result_is_governed():
    result = assess()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = assess(failed_components=("event_bus",))
    data = result.as_dict()
    assert data["isolated"] is True
    assert data["failed_components"] == ["event_bus"]


def test_isolation_is_deterministic():
    first = assess(
        failed_components=("event_bus",),
        failures=("unavailable",),
    )
    second = assess(
        failed_components=("event_bus",),
        failures=("unavailable",),
    )
    assert first == second


def test_multiple_failures_remain_independent():
    result = assess(
        failed_components=("event_bus", "intelligence"),
    )
    assert result.failed_components == ("event_bus", "intelligence")
    assert result.healthy_components == ("runtime",)
    assert result.isolated is True
