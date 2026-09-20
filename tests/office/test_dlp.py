from yoma.office.models.dlp import FileTransferEvent
from yoma.office.services.dlp import DLPEngine


def test_approved_destination_is_allowed():

    engine = DLPEngine(
        approved_destinations={"company-share"}
    )

    event = FileTransferEvent(
        employee_id="EMP001",
        source_path="company://reports/report.pdf",
        destination="company-share",
        classification="confidential",
    )

    decision = engine.evaluate(event)

    assert decision.action == "allow"
    assert decision.risk == "low"
    assert not decision.alert_required
    assert not decision.block_required


def test_confidential_file_to_removable_device_is_blocked():

    engine = DLPEngine()

    event = FileTransferEvent(
        employee_id="EMP001",
        source_path="company://finance/payroll.xlsx",
        destination="USB-001",
        classification="confidential",
        device_type="removable",
        device_id="USB-001",
    )

    decision = engine.evaluate(event)

    assert decision.action == "block"
    assert decision.risk == "high"
    assert decision.block_required


def test_confidential_file_to_unknown_destination_alerts():

    engine = DLPEngine()

    event = FileTransferEvent(
        employee_id="EMP001",
        source_path="company://research/data.xlsx",
        destination="unknown-destination",
        classification="confidential",
    )

    decision = engine.evaluate(event)

    assert decision.action == "alert"
    assert decision.risk == "medium"
    assert decision.alert_required


def test_normal_internal_file_is_allowed():

    engine = DLPEngine()

    event = FileTransferEvent(
        employee_id="EMP001",
        source_path="company://documents/notice.pdf",
        destination="company-internal",
        classification="internal",
    )

    decision = engine.evaluate(event)

    assert decision.action == "allow"


def test_internal_file_to_unapproved_removable_device_alerts():

    engine = DLPEngine()

    event = FileTransferEvent(
        employee_id="EMP001",
        source_path="company://documents/notice.pdf",
        destination="USB-001",
        classification="internal",
        device_type="removable",
    )

    decision = engine.evaluate(event)

    assert decision.action == "alert"
    assert decision.alert_required


def test_explicitly_blocked_destination_is_blocked():

    engine = DLPEngine(
        blocked_destinations={"unauthorized-storage"}
    )

    event = FileTransferEvent(
        employee_id="EMP001",
        source_path="company://data/file.pdf",
        destination="unauthorized-storage",
        classification="internal",
    )

    decision = engine.evaluate(event)

    assert decision.action == "block"
    assert decision.block_required


def test_missing_destination_is_blocked():

    engine = DLPEngine()

    event = FileTransferEvent(
        employee_id="EMP001",
        source_path="company://data/file.pdf",
        destination="",
    )

    decision = engine.evaluate(event)

    assert decision.action == "block"
