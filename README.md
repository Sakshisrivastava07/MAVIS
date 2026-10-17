# MAVIS: local virtual phone prototype

MAVIS is a student demo of a hospital call intake assistant. Calls run between a browser virtual phone and a self-hosted LiveKit server; no SIM, phone provider, public phone number, or cloud host is used. Use invented caller IDs and synthetic examples only. This is a demonstration, not a medical service. Never enter real patient information.

## What runs locally

- LiveKit dev server carries WebRTC audio on `ws://127.0.0.1:7880`.
- Speaches runs in a CPU Docker container at `http://localhost:8000/v1` and handles local speech recognition and speech generation.
- The Python Agent joins each room and uses Groq for its language model. The LLM request is the only application data sent outside the computer.
- FastAPI on port 8001 creates unique rooms and short-lived browser tokens.
- `web/index.html` is a plain browser phone at port 5500.

See [docs/architecture.md](docs/architecture.md) for a diagram.

## Files in plain language

- `agent/agent.py`: LiveKit voice worker, the AI's prompt, speech engines and event log.
- `api/server.py`: local health endpoint and room-token creation.
- `web/index.html`: phone screen, keypad, microphone and audio playback.
- `scripts/start-livekit.ps1` and `.sh`: start LiveKit natively.
- `scripts/start-speaches.ps1` and `.sh`: start Speaches CPU in Docker with a saved model cache.
- `scripts/run-app.ps1` and `.sh`: open the web phone, token API and agent.
- `scripts/smoke_test.py`: checks the local services, model round trip, Groq and token API.
- `docs/architecture.md`: explains how audio and tokens move through the demo.
- `.env.example` and the service-specific examples: safe starting configuration; put your actual key only in the ignored root `.env`.

## Setup (Windows)

Python 3.11 and Docker CLI are available in the current workspace. A Windows LiveKit server binary (version 1.13.7) is already present at `tools/livekit-server.exe`, and the start script uses it. For another OS, download the matching binary from [LiveKit Server releases](https://github.com/livekit/livekit/releases). Docker Desktop is installed but must be running. Copy the Groq API key from your account into the root `.env` file. Do not put it in source code.

From the project root in PowerShell:

```powershell
Copy-Item agent/.env.example .env
# Edit .env and set GROQ_API_KEY. Keep the local model names already listed.
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r agent/requirements.txt -r api/requirements.txt
```

The dependency bounds resolve and were installed with Python 3.11 on Windows. The common `.venv` is ignored by git.

## Setup (macOS/Linux)

Install Python 3.11+, Docker Engine/Desktop, and the `livekit-server` binary for your OS from [LiveKit Server releases](https://github.com/livekit/livekit/releases). Then run:

```sh
cp agent/.env.example .env
# Edit .env and set GROQ_API_KEY.
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r agent/requirements.txt -r api/requirements.txt
```

## Run order: exactly five terminals

Keep each command running in its own terminal, all from the MAVIS folder.

1. PowerShell: `./scripts/start-livekit.ps1` (macOS/Linux: `sh scripts/start-livekit.sh`)
2. PowerShell: `./scripts/start-speaches.ps1` (macOS/Linux: `sh scripts/start-speaches.sh`)
3. PowerShell: `.\.venv\Scripts\python.exe -m uvicorn api.server:app --host 127.0.0.1 --port 8001` (macOS/Linux: `.venv/bin/python -m uvicorn api.server:app --host 127.0.0.1 --port 8001`)
4. PowerShell: `.\.venv\Scripts\python.exe agent\agent.py dev` (macOS/Linux: `.venv/bin/python agent/agent.py dev`)
5. PowerShell: `.\.venv\Scripts\python.exe -m http.server 5500 --directory web` (macOS/Linux: `.venv/bin/python -m http.server 5500 --directory web`)

The LiveKit dev server uses `devkey` / `secret` by design. This is for local development only.

## Download Speaches speech models

Speaches explicitly downloads models; merely starting the container does not install them. Its documented route is `POST /v1/models/{model}`. After starting Speaches, open another PowerShell terminal:

```powershell
# See exact model IDs known by this running Speaches version
Invoke-RestMethod http://localhost:8000/v1/registry?task=automatic-speech-recognition
Invoke-RestMethod http://localhost:8000/v1/registry?task=text-to-speech
# Install the selected IDs (downloads can take time)
Invoke-RestMethod -Method Post http://localhost:8000/v1/models/Systran/faster-whisper-small
Invoke-RestMethod -Method Post http://localhost:8000/v1/models/speaches-ai/Kokoro-82M-v1.0-ONNX
Invoke-RestMethod http://localhost:8000/v1/models
```

The documented sample voice for the Kokoro ONNX model is `af_heart`. On a slow laptop, choose an available `tiny.en` or `base.en` faster-whisper model from the registry and set `STT_MODEL` in `.env` to its exact ID. The startup volume persists the Hugging Face model cache. Verify IDs with the running service's `/v1/models` list if its version changes.

The default Groq model is `openai/gpt-oss-20b` (available in the current Groq API documentation). Models and free-plan access can change; verify it is available to your account. The smoke check makes a tiny real request and reports any key, model, access, or quota issue. Never upgrade to a paid tier for this project.

## Try the phone

After all five services are running, run `python scripts/smoke_test.py`. For a true call test, open `http://localhost:5500`, allow microphone access, and click Call. Use a headset to avoid echo. Expected greeting: “Hello, this is MAVIS, an AI assistant. This is a demo. How can I help you?” Speak only fictional examples. Click Hang up to end.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Token API down | Terminal 3 stopped or port 8001 blocked | Restart it; open `http://127.0.0.1:8001/health`. |
| Agent not registered / no greeting | Agent terminal stopped, LiveKit unavailable, or missing room dispatch | Start terminals 1 and 4; check the Agent logs for connection errors. |
| No audio | Browser microphone permission, playback blocked, or Speaches model missing | Use localhost, allow microphone, click the page if playback needs activation, download both models, and check Speaches logs. |
| Groq 429 / model unavailable | Free-plan rate limit or model access changed | Wait for the quota window and check the model ID/account access; do not enable paid billing. |
| Whisper responds slowly | CPU model too large or first run downloads/model warms up | Let initial startup finish or select an available `tiny.en`/`base.en` model. |

## Verify Stage 1–3

`python scripts/smoke_test.py` prints one PASS or FAIL per check: LiveKit socket, Speaches model list, generated speech-to-text round trip, Groq chat, and `POST /call/start`. The call check requires the API to be running; the other service checks require their respective service and models. It never uses real patient data.

## Current implementation limits

- This prototype targets the installed LiveKit Agents 1.8.x API. Runtime compatibility with a local server and Speaches image could not be exercised until those services and model downloads are started.
- The latency CSV records framework event timestamps as UTC rows. `llm_response_ready` is the completed assistant message event, not the first streamed token; first-token timing and paired per-turn durations remain to be instrumented.
- `safety_gate()` is intentionally a no-op placeholder. No medical rules or clinical decisions are implemented.
- The web client uses the pinned LiveKit browser bundle URL from jsDelivr; initial page load needs internet access for that open-source package.

## Stage 4

Stage 4 is intentionally not implemented yet. It adds the audio evaluation, latency summary, nurse join and simulated follow-up call flows after the user asks to continue.

Before the first agent run, warm the packaged local VAD assets if needed: `.\.venv\Scripts\python.exe agent\agent.py download-files` on Windows, or `.venv/bin/python agent/agent.py download-files` on macOS/Linux. LiveKit Agents 1.8.4 includes this CLI command; this project has not needed a downloaded turn model in the inspected VAD configuration.
