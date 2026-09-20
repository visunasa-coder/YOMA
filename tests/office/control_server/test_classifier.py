from yoma.office.control_server.classifier import HardwareClassifier


def test_attendance_device_is_classified():
    classifier = HardwareClassifier()

    device = {
        "class": "USB",
        "name": "ZKTeco Fingerprint Attendance Device",
        "instance_id": "USB\\VID_TEST",
    }

    assert classifier.classify(device) == "attendance"


def test_security_device_is_classified():
    classifier = HardwareClassifier()

    device = {
        "class": "Camera",
        "name": "IP Camera",
        "instance_id": "CAMERA\\TEST",
    }

    assert classifier.classify(device) == "security"


def test_bluetooth_device_is_classified():
    classifier = HardwareClassifier()

    device = {
        "class": "Bluetooth",
        "name": "Example Bluetooth Device",
        "instance_id": "BTH\\TEST",
    }

    assert classifier.classify(device) == "bluetooth"


def test_network_device_is_classified():
    classifier = HardwareClassifier()

    device = {
        "class": "Net",
        "name": "Ethernet Controller",
        "instance_id": "PCI\\TEST",
    }

    assert classifier.classify(device) == "network"


def test_normal_windows_device_is_other():
    classifier = HardwareClassifier()

    device = {
        "class": "Processor",
        "name": "AMD Ryzen Processor",
        "instance_id": "ACPI\\TEST",
    }

    assert classifier.classify(device) == "other"
