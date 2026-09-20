from yoma.office.commercial_product import (
    CommercialEdition,
    CommercialProductCatalog,
)
from yoma.office.commercial_release_candidate_runtime import (
    CommercialReleaseCandidateRuntime,
)
from yoma.office.release_manifest import (
    ReleaseComponent,
    ReleaseManifest,
)


def build_inputs():
    edition = CommercialEdition(
        edition_id="enterprise",
        display_name="YOMA Enterprise",
        target_market="enterprise",
        capabilities=("intelligence", "deployment"),
    )

    catalog = CommercialProductCatalog(
        editions=(edition,),
    )

    component = ReleaseComponent(
        name="yoma-core",
        version="1.0.0",
        component_type="runtime",
    )

    manifest = ReleaseManifest(
        product_name="YOMA",
        product_version="1.0.0",
        release_channel="commercial",
        vendor_name="VP Technologies",
        components=(component,),
    )

    return catalog, manifest


def assess(**overrides):
    catalog, manifest = build_inputs()

    values = {
        "product_catalog": catalog,
        "release_manifest": manifest,
        "product_identity_valid": True,
        "release_manifest_valid": True,
        "integrity_available": True,
        "licensing_ready": True,
        "deployment_ready": True,
        "hardening_ready": True,
        "enterprise_validation_ready": True,
    }
    values.update(overrides)

    return CommercialReleaseCandidateRuntime().assess(**values)


def test_complete_release_candidate_is_ready():
    result = assess()
    assert result.ready is True
    assert result.release_candidate is True


def test_product_failure_blocks_candidate():
    result = assess(product_identity_valid=False)
    assert result.ready is False
    assert result.product_valid is False


def test_manifest_failure_blocks_candidate():
    result = assess(release_manifest_valid=False)
    assert result.ready is False
    assert result.manifest_valid is False


def test_integrity_failure_blocks_candidate():
    result = assess(integrity_available=False)
    assert result.ready is False
    assert result.integrity_valid is False


def test_licensing_failure_blocks_candidate():
    result = assess(licensing_ready=False)
    assert result.ready is False
    assert result.commercial_ready is False


def test_deployment_failure_blocks_candidate():
    result = assess(deployment_ready=False)
    assert result.ready is False


def test_hardening_failure_blocks_candidate():
    result = assess(hardening_ready=False)
    assert result.ready is False


def test_enterprise_validation_failure_blocks_candidate():
    result = assess(enterprise_validation_ready=False)
    assert result.ready is False


def test_product_metadata_is_validated():
    result = assess()
    assert result.product_valid is True


def test_manifest_metadata_is_validated():
    result = assess()
    assert result.manifest_valid is True


def test_integrity_hash_is_validated():
    result = assess()
    assert result.integrity_valid is True


def test_issues_are_preserved():
    result = assess(issues=("licensing", "deployment"))
    assert result.issues == ("licensing", "deployment")


def test_issues_are_deduplicated():
    result = assess(issues=("licensing", "licensing", "deployment"))
    assert result.issues == ("licensing", "deployment")


def test_result_requires_human_approval():
    result = assess()
    assert result.requires_human_approval is True


def test_release_candidate_is_not_executable():
    result = assess()
    assert result.executable is False


def test_failed_candidate_remains_non_executable():
    result = assess(hardening_ready=False)
    assert result.ready is False
    assert result.release_candidate is False
    assert result.executable is False


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["ready"] is True
    assert data["release_candidate"] is True
    assert data["integrity_valid"] is True


def test_runtime_is_deterministic():
    first = assess(issues=("licensing", "deployment"))
    second = assess(issues=("licensing", "deployment"))
    assert first == second


def test_release_candidate_requires_all_commercial_gates():
    result = assess(
        licensing_ready=False,
        deployment_ready=False,
        hardening_ready=False,
        enterprise_validation_ready=False,
    )
    assert result.ready is False
    assert result.commercial_ready is False
