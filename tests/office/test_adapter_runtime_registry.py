from yoma.office.adapters import AdapterRegistry, AdapterRuntimeManager


def test_runtime_manager_preserves_empty_registry_instance():
    registry = AdapterRegistry()

    manager = AdapterRuntimeManager(registry)

    assert manager.registry is registry
