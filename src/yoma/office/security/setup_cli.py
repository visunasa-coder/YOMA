"""YOMA first-run setup assistant.

This is deliberately safe:
- it never prints secrets;
- importing OAuth configuration does not authenticate YOMA;
- Google authorization remains a human administrator action;
- no execution authority is created.
"""

from __future__ import annotations

import argparse

from .setup_service import YomaSetupService


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="YOMA Enterprise First-Run Setup"
    )

    parser.add_argument(
        "--google-json",
        help="Path to the organization's Google OAuth JSON",
    )

    args = parser.parse_args(argv)

    service = YomaSetupService()

    print()
    print("=" * 68)
    print("                    YOMA ENTERPRISE")
    print("                 FIRST-RUN SETUP ASSISTANT")
    print("=" * 68)
    print()
    print("Welcome to YOMA.")
    print()
    print("YOMA features:")

    for feature in service.welcome()["features"]:
        print(f"  [OK] {feature}")

    print()
    print("GOOGLE WORKSPACE SETUP")
    print("-" * 68)

    for index, instruction in enumerate(
        service.instructions(),
        1,
    ):
        print(f"{index}. {instruction}")

    print()

    path = args.google_json

    if not path:
        path = input(
            "Select the downloaded Google OAuth JSON path "
            "(or press Enter to skip): "
        ).strip()

    if path:
        result = service.import_google_json(path)

        if not result["success"]:
            print()
            print("[ERROR] OAuth JSON validation failed.")
            print(result["validation"]["error"])
            return 2

        print()
        print("[OK] OAuth configuration validated.")
        print("[OK] Configuration provisioned securely.")
        print()
        print("Next: YOMA must complete Google's browser authorization.")
        print("The OAuth client JSON itself does NOT authenticate YOMA.")
        service.begin_google_authorization()
    else:
        print("Google setup skipped.")

    print()
    print("Current setup:")
    for key, value in service.status().as_dict().items():
        print(f"  {key:32} {value}")

    print()
    print("Execution authority: FALSE")
    print("Self-authorized execution: BLOCKED")
    print("Human approval boundary: REQUIRED")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
