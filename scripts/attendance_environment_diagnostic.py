from pprint import pprint

from yoma.office.services.attendance_environment_assessment import (
    AttendanceEnvironmentAssessment,
)
from yoma.office.services.hardware_discovery import (
    HardwareDiscoveryService,
)

print("=" * 70)
print("YOMA ATTENDANCE ENVIRONMENT - LIVE READ-ONLY DIAGNOSTIC")
print("=" * 70)

discovery = HardwareDiscoveryService()

print("\n[1] Collecting local environment...")
environment = discovery.discover()

print("Platform:", environment.get("platform"))

print("\nWindows devices discovered:",
      len(environment.get("windows_devices", [])))

print("Serial ports discovered:",
      len(environment.get("serial_ports", [])))

print("\n[2] Running attendance assessment...")
assessment = AttendanceEnvironmentAssessment()
result = assessment.assess(environment)

print("\nCandidate count:", result["candidate_count"])
print("Discovery only:", result["discovery_only"])
print("Human approval required:",
      result["requires_human_approval"])
print("Executable:", result["executable"])
print("Activation allowed:",
      result["activation_allowed"])

print("\n[3] Attendance candidates:")

if not result["candidates"]:
    print("  NONE DETECTED")
else:
    for index, candidate in enumerate(result["candidates"], 1):
        print(f"\n--- Candidate {index} ---")
        print("Adapter:", candidate["adapter"])
        print("Category:", candidate["category"])
        print("Transport:",
              candidate["candidate"]["transport"])
        print("Confidence:", candidate["confidence"])
        print("Source:", candidate["source"])
        print("Human approval:",
              candidate["requires_human_approval"])
        print("Executable:", candidate["executable"])
        print("Activation allowed:",
              candidate["activation_allowed"])

        print("Device:")
        pprint(candidate["candidate"]["device"])

print("\n" + "=" * 70)
print("READ-ONLY DIAGNOSTIC COMPLETE")
print("=" * 70)

input("\nPress ENTER to finish...")
