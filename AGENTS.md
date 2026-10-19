# MAVIS project rules for future Codex sessions

This is a 7th-semester group project: a free, local prototype of a simulated hospital call-centre voice assistant. Work only inside this project. Calls use a browser virtual phone over WebRTC. Never add real numbers, emergency numbers, SIP providers, real patient details, paid services, or cloud hosting. Groq's free tier is the sole external model service; read its API key only from the ignored root `.env` as `GROQ_API_KEY`. Never commit secrets.

Use Python 3.11+. Keep code simple, type clearly where useful, and explain each file with a short header comment. The local app has LiveKit server, Speaches CPU in Docker, a Python LiveKit Agent, a FastAPI call-token service, and a plain HTML/JS dialer. Synthetic caller ID only.

Verify changing APIs from the installed package source/docs and the running Speaches model registry/list. Do not invent package methods, model IDs, voice IDs, or behavior. Report any verification you could not perform. In this workspace, Python 3.11 is available and `tools/livekit-server.exe` is version 1.13.7. The common isolated environment is `.venv/`.

Build in stages from the user's original brief. Complete Stages 1, 2 and 3, run each requested verification, report results and manual steps, then STOP. Do not start Stage 4 (audio evaluation, nurse page, follow-up page) until the user explicitly says `continue`.

Keep `.env`, virtual environments, downloaded models, Node modules and Python caches out of git. `.env.example` files are safe templates. For browser microphone access use localhost. Do not enter any real clinical information: this is a demo, not medical care. `safety_gate()` is only a future placeholder and must not be described as a working rule-based emergency feature.

Keep docs/PROJECT_PROGRESS.md current whenever project work changes implementation, verification, or scope. Update it in the same change, with evidence for completed work. Do not mark checks as passing unless they were run.
