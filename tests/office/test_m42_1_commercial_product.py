from yoma.office.commercial_product import (
    CommercialEdition,
    CommercialProductCatalog,
    ProductMetadata,
)


def test_default_product_metadata():
    product = ProductMetadata()
    assert product.product_name == "YOMA"
    assert product.product_version == "1.0.0"
    assert product.release_channel == "commercial"
    assert product.vendor_name == "VP Technologies"


def test_product_metadata_serializes():
    data = ProductMetadata().as_dict()
    assert data["product_name"] == "YOMA"
    assert data["product_version"] == "1.0.0"


def test_product_metadata_rejects_empty_name():
    try:
        ProductMetadata(product_name="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_product_metadata_rejects_empty_version():
    try:
        ProductMetadata(product_version="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_product_metadata_rejects_empty_vendor():
    try:
        ProductMetadata(vendor_name="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_edition_is_constructed():
    edition = CommercialEdition(
        edition_id="enterprise",
        display_name="YOMA Enterprise",
        target_market="enterprise",
        capabilities=("intelligence", "deployment"),
    )
    assert edition.edition_id == "enterprise"


def test_edition_serializes():
    edition = CommercialEdition(
        edition_id="professional",
        display_name="YOMA Professional",
        target_market="professional",
        capabilities=("intelligence",),
    )
    data = edition.as_dict()
    assert data["edition_id"] == "professional"
    assert data["capabilities"] == ["intelligence"]


def test_edition_rejects_empty_id():
    try:
        CommercialEdition(
            edition_id="",
            display_name="YOMA",
            target_market="enterprise",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_edition_requires_tuple_capabilities():
    try:
        CommercialEdition(
            edition_id="enterprise",
            display_name="YOMA Enterprise",
            target_market="enterprise",
            capabilities=["intelligence"],
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Expected TypeError")


def test_catalog_contains_product_and_editions():
    edition = CommercialEdition(
        edition_id="enterprise",
        display_name="YOMA Enterprise",
        target_market="enterprise",
    )
    catalog = CommercialProductCatalog(
        editions=(edition,),
    )
    data = catalog.catalog()
    assert "product" in data
    assert len(data["editions"]) == 1


def test_catalog_lookup():
    edition = CommercialEdition(
        edition_id="enterprise",
        display_name="YOMA Enterprise",
        target_market="enterprise",
    )
    catalog = CommercialProductCatalog(
        editions=(edition,),
    )
    assert catalog.get_edition("enterprise") == edition


def test_missing_edition_returns_none():
    catalog = CommercialProductCatalog()
    assert catalog.get_edition("missing") is None


def test_catalog_is_deterministic():
    edition = CommercialEdition(
        edition_id="enterprise",
        display_name="YOMA Enterprise",
        target_market="enterprise",
        capabilities=("intelligence", "deployment"),
    )
    first = CommercialProductCatalog(editions=(edition,)).catalog()
    second = CommercialProductCatalog(editions=(edition,)).catalog()
    assert first == second


def test_product_description_is_present():
    product = ProductMetadata()
    assert product.product_description


def test_commercial_channel_is_explicit():
    product = ProductMetadata()
    assert product.release_channel == "commercial"
