import json
import queue
import sys
import urllib.request
import urllib.error
import getpass

import sounddevice as sd
from vosk import Model, KaldiRecognizer


API_BASE = "http://127.0.0.1:8765"
LOGIN_URL = API_BASE + "/auth/login"
ASSISTANT_URL = API_BASE + "/assistant/query"

MODEL_PATH = r".\models\vosk-model-small-en-us-0.15"

MIC_DEVICE = 1
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 4000

audio_queue = queue.Queue()


def post_json(url: str, payload: dict, token: str | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def login(username: str, password: str) -> str:
    response = post_json(
        LOGIN_URL,
        {
            "username": username,
            "password": password,
        },
    )

    token = response.get("access_token")

    if not token:
        raise RuntimeError("YOMA login did not return an access token")

    return token


def ask_yoma(text: str, token: str) -> dict:
    return post_json(
        ASSISTANT_URL,
        {
            "query": text,
            "limit": 5,
        },
        token=token,
    )


def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[AUDIO] {status}", file=sys.stderr)

    audio_queue.put(bytes(indata))


print()
print("=" * 70)
print("              YOMA EMBEDDED VOICE ASSISTANT")
print("=" * 70)
print()
print("MICROPHONE")
print("    ↓")
print("VOSK LOCAL STT")
print("    ↓")
print("YOMA AUTHENTICATION")
print("    ↓")
print("YOMA ASSISTANT GATEWAY")
print("    ↓")
print("YOMA RESPONSE")
print()
print("STT  : LOCAL / OFFLINE")
print("API  : " + API_BASE)
print("AUDIO: MEMORY ONLY")
print()

# ------------------------------------------------------------
# 1. Load STT
# ------------------------------------------------------------

print("[1/4] Loading offline speech model...")

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)

print("      PASS")

# ------------------------------------------------------------
# 2. Login
# ------------------------------------------------------------

print("[2/4] Authenticating with YOMA...")
print()

username = input("YOMA username: ")
password = getpass.getpass("YOMA password: ")

try:
    token = login(username, password)
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")

    print()
    print("      LOGIN FAILED")
    print(f"      HTTP {exc.code}")
    print(body[:500])

    sys.exit(1)

print()
print("      LOGIN PASS")

# ------------------------------------------------------------
# 3. Test assistant gateway
# ------------------------------------------------------------

print("[3/4] Testing assistant gateway...")

try:
    response = ask_yoma("Hello YOMA", token)

    print("      PASS")
    print(
        f"      Provider: "
        f"{response.get('provider')}"
    )
    print(
        f"      Generation: "
        f"{response.get('generation_status')}"
    )

except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")

    print("      FAILED")
    print(f"      HTTP {exc.code}")
    print(body[:1000])

    sys.exit(1)

# ------------------------------------------------------------
# 4. Microphone
# ------------------------------------------------------------

print("[4/4] Opening microphone...")
print("      Device: Headset (boAt Rockerz 518)")
print("      PASS")
print()

print("=" * 70)
print("🎙️  YOMA IS LISTENING")
print("=" * 70)
print()
print("Speak normally.")
print("Say 'exit' to stop.")
print()

try:

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        device=MIC_DEVICE,
        dtype="int16",
        channels=CHANNELS,
        callback=audio_callback,
    ):

        while True:

            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):

                result = json.loads(
                    recognizer.Result()
                )

                text = result.get(
                    "text",
                    ""
                ).strip()

                if not text:
                    continue

                print()
                print(f"YOU : {text}")

                if text.lower() in {
                    "exit",
                    "quit",
                    "stop yoma",
                    "goodbye yoma",
                }:

                    print()
                    print("YOMA: Shutting down safely.")
                    break

                print("YOMA: Thinking...")

                try:

                    response = ask_yoma(
                        text,
                        token
                    )

                    answer = response.get(
                        "answer"
                    )

                    if answer:
                        print()
                        print(
                            f"YOMA: {answer}"
                        )

                    else:
                        print(
                            "YOMA:",
                            response.get(
                                "reason",
                                "No response generated."
                            )
                        )

                    print()
                    print(
                        "[Provider:",
                        response.get(
                            "provider"
                        ),
                        "]"
                    )

                except urllib.error.HTTPError as exc:

                    body = exc.read().decode(
                        "utf-8",
                        errors="replace"
                    )

                    print(
                        f"YOMA ERROR: HTTP {exc.code}"
                    )

                    print(
                        body[:1000]
                    )

                except Exception as exc:

                    print(
                        f"YOMA ERROR: {exc}"
                    )

                print()
                print("🎙️ Listening...")

except KeyboardInterrupt:

    print()
    print(
        "YOMA: Interrupted safely."
    )

finally:

    print()
    print("=" * 70)
    print(
        "YOMA EMBEDDED VOICE ASSISTANT STOPPED"
    )
    print("=" * 70)