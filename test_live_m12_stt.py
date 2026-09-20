import json
import queue
import time

import sounddevice as sd
from vosk import Model, KaldiRecognizer


MODEL_PATH = r".\models\vosk-model-small-en-us-0.15"
DEVICE = 1
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 4000
TEST_SECONDS = 10

audio_queue: queue.Queue[bytes] = queue.Queue()


def audio_callback(indata, frames, time_info, status) -> None:
    if status:
        print(f"\n[audio] {status}")

    audio_queue.put(bytes(indata))


print()
print("=" * 60)
print("YOMA M12.4 LIVE OFFLINE STT TEST")
print("=" * 60)
print()
print("Microphone : Headset (boAt Rockerz 518)")
print("STT        : Vosk")
print("Mode       : OFFLINE / LOCAL")
print(f"Duration   : {TEST_SECONDS} seconds")
print()
print("Loading model...")

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

print("Model loaded.")
print()
print("🎙️ SPEAK NOW")
print('Say: "Hello YOMA, this is a live microphone test."')
print()

start = time.monotonic()

try:
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        device=DEVICE,
        dtype="int16",
        channels=CHANNELS,
        callback=audio_callback,
    ):
        while time.monotonic() - start < TEST_SECONDS:
            try:
                data = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()

                if text:
                    print(f"\n[FINAL] {text}")
            else:
                partial = json.loads(recognizer.PartialResult())
                text = partial.get("partial", "").strip()

                if text:
                    print(f"\r[LIVE] {text:<80}", end="", flush=True)

    final_result = json.loads(recognizer.FinalResult())
    final_text = final_result.get("text", "").strip()

    print()
    print()

    if final_text:
        print(f"[FINAL] {final_text}")

    print()
    print("=" * 60)
    print("M12.4 LIVE STT TEST COMPLETE")
    print("=" * 60)
    print()

    if final_text:
        print("RESULT: STT RECEIVED SPEECH ✅")
        print(f"Transcript: {final_text}")
    else:
        print("RESULT: NO SPEECH WAS RECOGNIZED ⚠️")
        print("Check the selected microphone and speak clearly.")

    print()
    print("Processing mode: LOCAL / OFFLINE")
    print("Audio file saved: NO")

except Exception as exc:
    print()
    print("M12.4 LIVE STT TEST FAILED ❌")
    print(f"Reason: {exc}")
    raise