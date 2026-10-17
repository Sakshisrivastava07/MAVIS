"""Stage 2/3 checks for local services, model inference, Groq, and call-token creation."""
import json
import os
import re
import socket
import struct
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
SPEACHES = os.getenv("SPEACHES_BASE_URL", "http://localhost:8000/v1").rstrip("/")


def check(name, fn):
    try:
        detail = fn()
        print(f"PASS {name}: {detail or 'OK'}")
    except Exception as exc:
        print(f"FAIL {name}: {exc}")


def livekit():
    with socket.create_connection(("127.0.0.1", 7880), timeout=2):
        return "TCP port 7880 accepts connections"


def speaches():
    with urllib.request.urlopen(SPEACHES + "/models", timeout=5) as response:
        data = json.load(response)
    model_ids = [item.get("id", "") for item in data.get("data", [])]
    if not model_ids:
        raise RuntimeError("No downloaded models found. Download STT/TTS models first.")
    return f"reachable; {len(model_ids)} models listed"


def speaches_roundtrip():
    import httpx
    tts_model = os.getenv("TTS_MODEL", "speaches-ai/Kokoro-82M-v1.0-ONNX")
    stt_model = os.getenv("STT_MODEL", "Systran/faster-whisper-small")
    with httpx.Client(timeout=180) as client:
        audio = client.post(SPEACHES + "/audio/speech", json={
            "model": tts_model, "voice": os.getenv("TTS_VOICE", "af_heart"),
            "input": "This is a local synthetic demo call.", "response_format": "wav",
        })
        audio.raise_for_status()
        response = client.post(SPEACHES + "/audio/transcriptions", data={"model": stt_model},
                               files={"file": ("sample.wav", audio.content, "audio/wav")})
        response.raise_for_status()
        transcript = response.json().get("text", "")
        if not transcript:
            raise RuntimeError(f"Empty transcription: {response.text[:200]}")
        expected = set(re.findall(r"[a-z]+", "This is a local synthetic demo call.".lower()))
        actual = set(re.findall(r"[a-z]+", transcript.lower()))
        overlap = len(expected & actual) / len(expected)
        if overlap < 0.5:
            raise RuntimeError(f"Transcript did not roughly match generated sentence ({overlap:.0%} word overlap): {transcript!r}")
        return f"transcribed generated audio: {transcript!r}"


def groq():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY missing in root .env")
    body = json.dumps({"model": os.getenv("LLM_MODEL", "openai/gpt-oss-20b"),
                       "messages": [{"role": "user", "content": "Reply with the single word READY."}],
                       "max_tokens": 8}).encode()
    request = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "MAVIS-smoke-test/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = json.load(response)["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        response_body = response_body.replace(key, "[REDACTED]")
        raise RuntimeError(f"Groq HTTP {exc.code} response body: {response_body}") from None
    return f"chat completion returned {text!r}"


def token_api():
    req = urllib.request.Request("http://127.0.0.1:8001/call/start",
        data=json.dumps({"caller_id": "555-010-2048"}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.load(response)
    if not data.get("token") or not data.get("room", "").startswith("call-"):
        raise RuntimeError(f"Unexpected response: {data}")
    return f"valid room {data['room']} and token received"


if __name__ == "__main__":
    checks = [("LiveKit reachable on 7880", livekit), ("Speaches /v1/models", speaches),
              ("Speaches TTS-to-STT round trip", speaches_roundtrip),
              ("Groq tiny completion", groq), ("POST /call/start", token_api)]
    for title, fn in checks:
        check(title, fn)


