from yoma.audio import AudioCapture, AudioCaptureLimits
from yoma.windows_audio import WindowsMicrophone


print()
print("=" * 60)
print("YOMA M12.3 LIVE MICROPHONE TEST")
print("=" * 60)
print()
print("Microphone: Headset (boAt Rockerz 518)")
print("Duration:   3 seconds")
print()
print("When ready, speak normally...")
print()

microphone = WindowsMicrophone(
    device=1,
    sample_rate=16000,
    channels=1,
)

capture = AudioCapture(
    device=microphone,
    limits=AudioCaptureLimits(
        max_seconds=3,
        max_bytes=5 * 1024 * 1024,
    ),
)

try:
    audio = capture.record()

    print()
    print("MICROPHONE TEST PASSED")
    print(f"Captured bytes: {len(audio):,}")
    print("Audio was kept in memory only.")
    print("Audio was NOT written to disk.")
    print()

except Exception as exc:
    print()
    print("MICROPHONE TEST FAILED")
    print(f"Reason: {exc}")
    print()
    raise