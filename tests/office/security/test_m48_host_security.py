from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from yoma.office.security import (
    AdaptiveAttackDefense,
    ConfigurationIntegrity,
    ConfigurationSnapshot,
    EmergencyContainment,
    FileSystemMonitor,
    FileSystemObservation,
    HostAccessBoundary,
    HostIdentity,
    HostSecurityPolicy,
    HostSecurityRuntime,
    HostTrustState,
    IntegrityVerifier,
    ProcessMonitor,
    ProcessObservation,
    ProcessRisk,
    SecretBoundary,
    SourceBlockState,
    SecuritySignal,
)


def test_host_policy_disables_ai_execution():
    policy = HostSecurityPolicy()

    assert policy.ai_execution_authority is False
    assert policy.human_review_for_remediation is True


def test_host_identity_requires_least_privilege():
    identity = HostIdentity(
        deployment_id="dep-1",
        service_name="YomaControlServer",
        account_name="YOMA-SVC",
    )

    assert identity.least_privilege_compliant is True


def test_admin_or_interactive_service_is_not_least_privilege():
    identity = HostIdentity(
        deployment_id="dep-1",
        service_name="YomaControlServer",
        account_name="Administrator",
        administrator_required=True,
    )

    assert identity.least_privilege_compliant is False


def test_unknown_host_is_not_trusted():
    identity = HostIdentity(
        deployment_id="dep-1",
        service_name="YomaControlServer",
        account_name="YOMA-SVC",
    )

    result = HostAccessBoundary().assess(
        identity,
        HostTrustState.UNKNOWN,
    )

    assert result.allowed is False


def test_compromised_host_is_denied():
    identity = HostIdentity(
        deployment_id="dep-1",
        service_name="YomaControlServer",
        account_name="YOMA-SVC",
    )

    result = HostAccessBoundary().assess(
        identity,
        HostTrustState.COMPROMISED,
    )

    assert result.allowed is False


def test_trusted_least_privilege_host_allowed():
    identity = HostIdentity(
        deployment_id="dep-1",
        service_name="YomaControlServer",
        account_name="YOMA-SVC",
    )

    result = HostAccessBoundary().assess(
        identity,
        HostTrustState.TRUSTED,
    )

    assert result.allowed is True
    assert result.executable is False


def test_secret_boundary_detects_plaintext_secret():
    result = SecretBoundary().inspect_configuration({
        "google_client_secret": "plaintext-secret",
    })

    assert result.safe is False


def test_secret_boundary_accepts_nonsecret_configuration():
    result = SecretBoundary().inspect_configuration({
        "region": "mumbai",
        "port": 8766,
    })

    assert result.safe is True


def test_integrity_verifier():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.bin"
        path.write_bytes(b"YOMA")

        expected = hashlib.sha256(b"YOMA").hexdigest()

        result = IntegrityVerifier().verify_file(
            path,
            expected,
        )

        assert result.verified is True


def test_integrity_verifier_detects_modification():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "test.bin"
        path.write_bytes(b"YOMA")

        expected = hashlib.sha256(b"ORIGINAL").hexdigest()

        result = IntegrityVerifier().verify_file(
            path,
            expected,
        )

        assert result.verified is False


def test_process_monitor_accepts_expected_process():
    result = ProcessMonitor().assess(
        ProcessObservation(
            process_name="YOMA-ControlServer.exe",
            expected=True,
        )
    )

    assert result.risk is ProcessRisk.NORMAL


def test_process_monitor_detects_unexpected_process():
    result = ProcessMonitor().assess(
        ProcessObservation(
            process_name="unknown.exe",
            expected=False,
        )
    )

    assert result.risk is ProcessRisk.SUSPICIOUS


def test_configuration_integrity_matches():
    snapshot = ConfigurationSnapshot("yoma", "abc")

    result = ConfigurationIntegrity().compare(
        snapshot,
        snapshot,
    )

    assert result.intact is True


def test_configuration_integrity_detects_change():
    result = ConfigurationIntegrity().compare(
        ConfigurationSnapshot("yoma", "abc"),
        ConfigurationSnapshot("yoma", "xyz"),
    )

    assert result.intact is False


def test_filesystem_monitor_normal_scope():
    result = FileSystemMonitor().assess(
        FileSystemObservation(
            path="C:/Program Files/YOMA",
            actor="YOMA-SVC",
            operation="read",
            approved_actor=True,
            approved_path=True,
        )
    )

    assert result.risk.value == "normal"


def test_filesystem_monitor_detects_unknown_actor():
    result = FileSystemMonitor().assess(
        FileSystemObservation(
            path="C:/Program Files/YOMA",
            actor="unknown",
            operation="read",
            approved_actor=False,
            approved_path=True,
        )
    )

    assert result.risk.value == "suspicious"


def test_adaptive_defense_watches_initial_failures():
    defense = AdaptiveAttackDefense()

    result = defense.observe(
        SecuritySignal(
            source_id="ip:203.0.113.10",
            signal="failed_authentication",
        )
    )

    assert result.state is SourceBlockState.ALLOWED


def test_adaptive_defense_escalates_repeated_failures():
    defense = AdaptiveAttackDefense()

    for _ in range(5):
        result = defense.observe(
            SecuritySignal(
                source_id="ip:203.0.113.10",
                signal="failed_authentication",
            )
        )

    assert result.state is SourceBlockState.BLOCKED


def test_adaptive_defense_critical_event_blocks_immediately():
    result = AdaptiveAttackDefense().observe(
        SecuritySignal(
            source_id="device:unknown",
            signal="privilege_attempt",
            severity="critical",
        )
    )

    assert result.state is SourceBlockState.BLOCKED


def test_adaptive_defense_tracks_source_separately():
    defense = AdaptiveAttackDefense()

    for _ in range(5):
        defense.observe(
            SecuritySignal(
                source_id="attacker-a",
                signal="failed_authentication",
            )
        )

    assert defense.check("attacker-a").state is SourceBlockState.BLOCKED
    assert defense.check("attacker-b").state is SourceBlockState.ALLOWED


def test_adaptive_defense_review_can_clear_block():
    defense = AdaptiveAttackDefense()

    for _ in range(5):
        defense.observe(
            SecuritySignal(
                source_id="attacker-a",
                signal="failed_authentication",
            )
        )

    result = defense.clear_after_review("attacker-a")

    assert result.state is SourceBlockState.ALLOWED
    assert result.score == 0


def test_containment_restricts_sensitive_execution():
    containment = EmergencyContainment()

    result = containment.enter_restricted(
        "suspected host compromise"
    )

    assert result.sensitive_execution_allowed is False
    assert result.executable is False


def test_containment_requires_approval_for_recovery():
    containment = EmergencyContainment()
    containment.enter_restricted("incident")

    result = containment.recover(approved=False)

    assert result.sensitive_execution_allowed is False


def test_containment_can_return_to_normal_after_approval():
    containment = EmergencyContainment()
    containment.enter_restricted("incident")

    result = containment.recover(approved=True)

    assert result.state.value == "normal"
    assert result.sensitive_execution_allowed is False


def test_host_runtime_status():
    runtime = HostSecurityRuntime()
    status = runtime.status()

    assert status["host_security"] == "active"
    assert status["adaptive_blocking"] is True
    assert status["temporary_blocking"] is True
    assert status["sensitive_execution_allowed"] is False
    assert status["requires_human_approval"] is True
    assert status["executable"] is False


def test_host_runtime_blocks_repeated_attack():
    runtime = HostSecurityRuntime()

    for _ in range(5):
        reputation = runtime.observe_attack(
            source_id="ip:203.0.113.50",
            signal="failed_authentication",
        )

    assert reputation.state is SourceBlockState.BLOCKED
    assert runtime.containment.state.value == "restricted"
    assert len(runtime.incidents()) == 1


def test_host_runtime_records_critical_attack():
    runtime = HostSecurityRuntime()

    reputation = runtime.observe_attack(
        source_id="device:bad-device",
        signal="privilege_attempt",
        severity="critical",
    )

    assert reputation.state is SourceBlockState.BLOCKED
    assert len(runtime.incidents()) == 1
    assert runtime.incidents()[0].severity == "critical"


def test_every_host_incident_requires_human_approval():
    runtime = HostSecurityRuntime()

    runtime.observe_attack(
        source_id="attacker",
        signal="privilege_attempt",
        severity="critical",
    )

    incident = runtime.incidents()[0]

    assert incident.requires_human_approval is True
    assert incident.executable is False


def test_m48_policy_has_all_major_controls():
    policy = HostSecurityPolicy()

    assert policy.service_account_least_privilege
    assert policy.protected_installation
    assert policy.secret_isolation
    assert policy.binary_integrity
    assert policy.configuration_integrity
    assert policy.process_monitoring
    assert policy.filesystem_monitoring
    assert policy.network_loopback_default
    assert policy.adaptive_blocking
    assert policy.emergency_containment


def test_source_block_has_expiry():
    defense = AdaptiveAttackDefense(block_seconds=60)

    result = defense.observe(
        SecuritySignal(
            source_id="ip:test",
            signal="privilege_attempt",
            severity="critical",
        )
    )

    assert result.blocked_until is not None
    assert result.blocked_until > 0


def test_blocking_does_not_execute_firewall_commands():
    defense = AdaptiveAttackDefense()

    result = defense.observe(
        SecuritySignal(
            source_id="ip:test",
            signal="configuration_tamper",
            severity="critical",
        )
    )

    assert result.state is SourceBlockState.BLOCKED
    assert result.executable is False
