# MAVIS Project Progress

> Living status document. Update this file whenever a feature is implemented, changed, verified, or deferred. Record the evidence and date in the change log so the whole team can see what is actually done.

**Last reviewed:** 2026-10-19
**Overall estimate:** about **65â€“70% of the currently documented project scope is implemented**. This is a feature-based estimate, not a count of lines of code. Core Stages 1â€“3 have substantial implementation; runtime verification is still outstanding, and Stage 4 has not started. Revisit the estimate when the full original brief or new requirements change the scope.

## Status key

- âœ… Implemented in the repository.
- ðŸŸ¡ Partly implemented, or implementation exists but still needs verification/completion.
- â¬œ Not implemented yet.
- â¸ï¸ Intentionally deferred until the user says `continue`.

## Progress by stage

| Stage / area | Status | Current evidence and remaining work |
| --- | --- | --- |
| Stage 1: Local app foundation | âœ… | Project structure, configuration templates, Python dependencies, local LiveKit and Speaches startup scripts, architecture notes, and setup instructions exist. Confirm a clean setup on the target machine if the environment changes. |
| Stage 2: Virtual phone and call connection | ðŸŸ¡ | `web/index.html` implements a browser dialer, synthetic caller ID, microphone permission, token request, LiveKit connection, audio playback, and hang-up. `api/server.py` implements health and call-start endpoints. Complete a real browser-to-agent call check and fix any integration issues found. |
| Stage 3: Voice agent and service checks | ðŸŸ¡ | `agent/agent.py` connects LiveKit, local Speaches STT/TTS, and Groq; `scripts/smoke_test.py` covers service/model connectivity, speech round trip, Groq, and token creation. Run the smoke checks with services/models available, verify package and running Speaches APIs against the installed versions, and document PASS/FAIL results. |
| Stage 4: Evaluation and extended call flows | â¸ï¸ | Not started. Per project instructions, do not begin until the user explicitly says `continue`. Planned items include audio evaluation, a nurse page/join flow, and simulated follow-up calls. |

## Implemented components

| Component | Status | Files / notes |
| --- | --- | --- |
| Local LiveKit development server | âœ… | `scripts/start-livekit.ps1`, `scripts/start-livekit.sh`; Windows binary is present in `tools/`. |
| Speaches CPU container and persistent model cache | âœ… | `scripts/start-speaches.ps1`, `scripts/start-speaches.sh`; model installation is a separate manual step. |
| FastAPI token service | âœ… | `api/server.py`; `GET /health`, `POST /call/start`, synthetic caller ID validation, room token creation. |
| Browser virtual phone | âœ… | `web/index.html`; microphone and audio behavior still needs end-to-end confirmation on the intended browser. |
| LiveKit voice agent | âœ… | `agent/agent.py`; includes prompt, local STT/TTS, Groq LLM, and latency event logging. Compatibility across the installed service versions still needs runtime verification. |
| Environment templates and secret hygiene | âœ… | Root and service `.env.example` templates exist; the root `.env` is ignored. Never commit API keys or real caller data. |
| Setup and architecture documentation | âœ… | `README.md` and `docs/architecture.md`. |
| Smoke-check script | âœ… | `scripts/smoke_test.py`; script exists, but this document does not claim its checks currently pass. |
| Latency data collection | ðŸŸ¡ | `eval/latency_log.csv` and event hooks exist. Current events are framework timestamps; `llm_response_ready` is not first-token timing, and paired per-turn latency summaries are not implemented. |
| Emergency/safety logic | â¬œ | `safety_gate()` is a no-op placeholder. No rule-based emergency detection or medical decision support exists. Do not present it as implemented. |

## Remaining work before Stage 4

Do these items while completing Stages 1â€“3. Run services only with fictional examples and the local demo configuration.

- [ ] Start LiveKit, Speaches, the API, and the agent using the documented run order.
- [ ] Query the running Speaches registry and `/v1/models`; install only model IDs shown by that service and confirm configured STT/TTS IDs and voice.
- [ ] Verify the installed LiveKit Agents and LiveKit API package interfaces used by the code against their installed package source/docs.
- [ ] Run `scripts/smoke_test.py`; record each check's result and relevant environment/version details below.
- [ ] Make a browser call at `http://localhost:5500`; confirm microphone capture, agent greeting, caller speech transcription, spoken reply, and hang-up.
- [ ] Fix any compatibility or call-flow defects found during the checks, then rerun the affected checks and update statuses.
- [ ] Capture any manual setup needed by another team member (Docker readiness, model download, free Groq key) in the README if it is missing.

## Stage 4 backlog â€” waiting for `continue`

These are planned from the project instructions, not completed features. Keep them deferred until the user explicitly authorizes Stage 4.

- [ ] Audio evaluation flow and defined evaluation outputs.
- [ ] Latency analysis: first-token timing and paired per-turn durations, with a summary/report.
- [ ] Nurse page and simulated nurse-join flow.
- [ ] Simulated follow-up call flow/page.
- [ ] Verify the Stage 4 flows using synthetic scenarios only and document their limitations.

## Verification record

| Date | Check | Result | Notes |
| --- | --- | --- | --- |
| 2026-10-19 | Repository implementation review | Reviewed | Confirmed source files and current project instructions. Runtime smoke test and browser call were not run during this review. |

When running verification, replace or append rows with actual results. Do not mark a check PASS based only on the existence of a script or source file.

## Update process for contributors

When a contributor completes or changes an item:

1. Update the relevant status and evidence above in the same change as the implementation.
2. Add a dated verification row when a check was actually run; include failures and limitations as well as passes.
3. Move unfinished tasks only when the implementation is present and reviewed. A planned feature or open pull request is not complete.
4. Keep Stage 4 items deferred until the user says `continue`.
5. Update the overall estimate when meaningful scope changes land, and state the basis for the new estimate.
