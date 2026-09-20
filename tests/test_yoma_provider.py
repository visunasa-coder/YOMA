from yoma.provider import (
    GenerationPolicy,
    YOMAProvider,
    provider_from_settings,
)


def test_yoma_provider_name():
    provider = YOMAProvider()
    assert provider.name == "yoma-native"


def test_yoma_provider_has_no_external_egress():
    provider = YOMAProvider()
    assert provider.requires_external_egress is False


def test_yoma_provider_hello():
    result = YOMAProvider().generate_answer(
        "hello",
        None,
        GenerationPolicy(),
    )
    assert result.generation_status == "generated"
    assert result.provider == "yoma-native"
    assert result.answer == "Hello. YOMA is ready."
    assert result.citations == ()
    assert result.reason is None


def test_yoma_provider_hi():
    result = YOMAProvider().generate_answer(
        "hi",
        None,
        GenerationPolicy(),
    )
    assert result.answer == "Hello. YOMA is ready."


def test_yoma_provider_status():
    result = YOMAProvider().generate_answer(
        "status",
        None,
        GenerationPolicy(),
    )
    assert result.answer == "YOMA is ready."


def test_yoma_provider_identity():
    result = YOMAProvider().generate_answer(
        "who are you",
        None,
        GenerationPolicy(),
    )
    assert result.answer == "I am YOMA, a local AI engine."


def test_yoma_provider_help():
    result = YOMAProvider().generate_answer(
        "help",
        None,
        GenerationPolicy(),
    )
    assert result.answer == (
        "YOMA is ready. Native AI capabilities are being developed."
    )


def test_yoma_provider_unsupported_query():
    result = YOMAProvider().generate_answer(
        "explain quantum computing",
        None,
        GenerationPolicy(),
    )
    assert result.answer == (
        "YOMA native engine cannot answer that request yet."
    )


def test_provider_from_settings_selects_yoma_native():
    class Settings:
        ai_provider = "yoma-native"

    provider = provider_from_settings(Settings())
    assert isinstance(provider, YOMAProvider)
