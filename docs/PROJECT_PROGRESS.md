# MAVIS Project Progress

> Living status document. Update this file whenever a feature is implemented, changed, verified, or deferred. Record the evidence and date in the change log so the whole team can see what is actually done.

**Last reviewed:** 2026-10-24
**Overall estimate:** about **70% of the currently documented project scope is implemented**. This feature-based estimate includes the new local demo intake and booking logic; its live call flow still needs verification, and Stage 4 pages and evaluation remain deferred.

## Status key

- âœ… Implemented in the repository.
- ðŸŸ¡ Partly implemented, or implementation exists but still needs verification/completion.
- â¬œ Not implemented yet.
- â¸ï¸ Intentionally deferred until the user says `continue`.

## Progress by stage

| Stage / area | Status | Current evidence and remaining work |
| --- | --- | --- |
| Stage 1: Local app foundation | âœ… | Project structure, configuration templates, Python dependencies, local LiveKit and Speaches startup scripts, architecture notes, and setup instructions exist. Confirm a clean setup on the target machine if the environment changes. |
| Stage 2: Virtual phone and call connection | ðŸŸ¡ | `web/index.html` and `api/server.py` provide the browser call and token flow. User reported prior voice audio worked but the latest call did not ask for a name; the opening greeting is now explicit and uninterruptible. Verify the revised flow in a fresh browser call. |
| Stage 3: Voice agent and service checks | ðŸŸ¡ | `agent/agent.py` now uses narrow per-stage agents and code-based LiveKit handoffs for name/age, symptom/red-flag branching, severity/history, routing, and optional booking. Source/API checks pass; a fresh browser call and smoke test remain. |
| Stage 4: Evaluation and extended call flows | â¸ï¸ | Not started. Per project instructions, do not begin until the user explicitly says `continue`. Planned items include audio evaluation, a nurse page/join flow, and simulated follow-up calls. |

## Implemented components

| Component | Status | Files / notes |
| --- | --- | --- |
| Local LiveKit development server | âœ… | `scripts/start-livekit.ps1`, `scripts/start-livekit.sh`; Windows binary is present in `tools/`. |
| Speaches CPU container and persistent model cache | âœ… | `scripts/start-speaches.ps1`, `scripts/start-speaches.sh`; model installation is a separate manual step. |
| FastAPI token service | âœ… | `api/server.py`; `GET /health`, `POST /call/start`, synthetic caller ID validation, room token creation. |
| Browser virtual phone | âœ… | `web/index.html`; microphone and audio behavior still needs end-to-end confirmation on the intended browser. |
| LiveKit voice agent | âœ… | `agent/agent.py`; includes the local STT/TTS and Groq wiring, proxy handling for local LiveKit, and latency event logging. A fresh browser call still needs verification. |
| Demo intake and booking flow | 🟡 | `agent/agent.py`; six stage-specific agents hand off through LiveKit function tools, share a typed session userdata object, use a Python red-flag check and deterministic department routing, and create in-memory demo bookings. Local API/source checks passed; a fresh audio call is still required. No actual nurse transfer, real booking, or portal exists. |
| Full call transcript recorder | 🟡 | `agent/agent.py` writes timestamped caller/MAVIS turns to JSON and readable TXT files under `transcripts/` when the LiveKit session closes. The code and empty-transcript behavior passed local checks; a full browser call and disconnect save remain unverified. Transcripts contain full conversation content and are for synthetic demo data only; they are not secure storage for real patient information without access control and encryption. |
| Environment templates and secret hygiene | âœ… | Root and service `.env.example` templates exist; the root `.env` is ignored. Never commit API keys or real caller data. |
| Setup and architecture documentation | âœ… | `README.md` and `docs/architecture.md`. |
| Smoke-check script | âœ… | `scripts/smoke_test.py`; script exists, but this document does not claim its checks currently pass. |
| Latency data collection | ðŸŸ¡ | `eval/latency_log.csv` and event hooks exist. Current events are framework timestamps; `llm_response_ready` is not first-token timing, and paired per-turn latency summaries are not implemented. |
| Demo red-flag phrase check | 🟡 | `safety_gate()` now does case-insensitive substring matching against an illustrative phrase list. It is not clinically reviewed, is not medical triage, and does not connect a caller to a nurse. |

## Remaining work before Stage 4

Do these items while completing Stages 1â€“3. Run services only with fictional examples and the local demo configuration.

- [ ] Start LiveKit, Speaches, the API, and the agent using the documented run order.
- [ ] Query the running Speaches registry and `/v1/models`; install only model IDs shown by that service and confirm configured STT/TTS IDs and voice.
- [x] Verify the installed LiveKit Agents function-tool interface and required-argument schema against the installed 1.8.4 package source.
- [x] Verify the installed LiveKit Agents 1.8.4 handoff return handling and shared `AgentSession.userdata` API against the installed package source.
- [ ] Verify the installed LiveKit API package interfaces used by the token service against the installed package source/docs.
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
| 2026-10-23 | LiveKit connection and voice diagnosis | Worker registration confirmed; per-call connection fix applied; browser call pending | Installed LiveKit Agents 1.8.4 source confirms worker connections default to `HTTPS_PROXY` / `HTTP_PROXY`. The worker registered at `ws://127.0.0.1:7880`, but the latest call log showed the job RTC connection failing in `ctx.connect()` before the agent could speak. `agent/agent.py` now bypasses proxy environment variables only while the job connects to local LiveKit, then restores them for Speaches/Groq requests. Both configured Speaches models are listed. A new browser call is needed to confirm audio end to end. |
| 2026-10-23 | Browser voice attempt | Failed: Speaches unreachable | The agent received a browser call, but its log reported an STT connection error. A follow-up request to `http://localhost:8000/v1/models` could not connect; Docker API access from the current shell was denied, so Speaches could not be restarted here. Keep the Speaches container running and repeat the browser call before claiming audio works. |
| 2026-10-23 | Speaches readiness after restart | Both configured models listed | The running registry contains the configured Whisper and Kokoro IDs. The live `GET /v1/models` endpoint now lists both; a new browser call is still needed to check audio after Speaches returned. |
| 2026-10-24 | Local call failure diagnosis | API unavailable; Speaches running with no models installed | From the project session, ports 5500, 7880, and 8000 accepted connections; port 8001 did not. The web page returned HTTP 200, but `/health` and `/call/start` could not connect, explaining browser `Failed to fetch`. Speaches `GET /v1/models` returned an empty list. Its live registry listed `Systran/faster-whisper-small` for STT and `speaches-ai/Kokoro-82M-v1.0-ONNX-fp16` for TTS; the latter differs from the current documented TTS model ID. Docker CLI inspection was denied in this session, so container status could not be confirmed through Docker. |
| 2026-10-24 | User-reported Speaches model download and prior voice audio | Models downloaded; prior voice audio reported working | User shared successful download output for registry-listed STT and TTS models and later reported that MAVIS audio worked. The new intake conversation still needs a fresh call. |
| 2026-10-24 | Configuration and credential review | Agent syntax valid; exposed example credential removed | `py_compile` succeeded for `agent/agent.py`. Git diff showed no user-specific changes to the prompt or greeting beyond the existing local LiveKit proxy fix. A Groq credential had been placed in tracked `agent/.env.example`; replaced it with an empty template value. Rotate that credential before further use, and keep the replacement only in ignored root `.env`. `eval/latency_log.csv` contains new runtime event rows, consistent with agent activity. |
| 2026-10-24 | User report | Prior agent audio | Reported working, not independently observed | User confirmed audio worked after the speech models were downloaded and the API was running. That confirmation predates the revised intake flow, which still needs a fresh call. |
| 2026-10-24 | LiveKit tool API and demo intake logic | Passed local source-level checks | Installed `livekit-agents` 1.8.4 exposes `function_tool` and `RunContext`. Introspection confirmed exactly three registered tools and required `patient_name`, `age`, and `symptom_description` schema fields. `py_compile` passed; local checks passed for emergency phrase matching, headache routing to Neurology, General Medicine fallback, and two sequential bookings with different tokens/doctors and slots 15 minutes apart. No live call with the revised conversation was run. |

| 2026-10-24 | User-reported name-order issue and prompt revision | Source check passed; browser call pending | User reported MAVIS was not asking for a name. The opening greeting now asks for the full name without interruptions, and the script explicitly redirects to the name before other questions. Urgency check is now before severity and further history. The emergency line states that no real transfer occurs; the demo has no patient portal. Syntax and static prompt-order checks passed; a live call was not run. |
| 2026-10-24 | Recheck after user reported no audio | API and Speaches TTS passed; browser/worker audio not verified | Ports 5500, 7880, 8000, and 8001 accepted TCP connections; API `/health` returned `{"status":"ok"}`. Speaches lists the configured Whisper and Kokoro fp16 models. A direct `/v1/audio/speech` request using the effective `.env` TTS settings returned HTTP 200 and 19,128 audio bytes (`audio/mp3`). The latency log has no entries after 2026-10-24T12:07:54Z, so this session cannot confirm that the current worker handled the latest call; restart the agent once and retry while watching its terminal. |
| 2026-10-24 | Deterministic intake agent handoffs | Source/API checks passed; browser call pending | Replaced the single long-prompt agent with NameAge, Symptom, Emergency, Severity, Routing, and Booking agents. Installed `livekit-agents` 1.8.4 source confirms a function tool can return an `Agent` directly for handoff, and `RunContext.userdata` accesses shared session userdata. `Agent.on_enter`, `session.say`, `SpeechHandle.wait_for_playout`, and `session.shutdown` are present in the installed source. `py_compile` passed; runtime introspection confirmed each required stage's tools and local checks confirmed red-flag matching and deterministic routing. The emergency and booking utterances are scripted; no actual nurse transfer or portal is claimed. Browser audio and a full call remain unverified. |
| 2026-10-24 | No agent voice report after handoff change | TTS service passed; worker call path pending | All service ports (5500, 7880, 8000, 8001) accepted TCP connections, API `/health` returned `ok`, and Speaches still lists the configured STT/TTS models. A fresh `/v1/audio/speech` request returned HTTP 200 with 13,056 MP3 bytes. `eval/latency_log.csv` had no new events after 2026-10-24T12:59:57Z at the time of this check; Windows denied process command-line inspection. Added console and CSV milestones for worker job receipt, LiveKit connection, browser join, session start, greeting playout, and each stage transition. Restart the agent and use these milestones to identify where a fresh call stops. |
| 2026-10-24 | Silent response after caller name | Root cause identified; scripted follow-up prompts added | Fresh event rows showed greeting TTS completed and `handoff_name_age_to_symptom` ran, with no subsequent `tts_first_audio`. `SymptomAgent` had no `on_enter` prompt, so the LLM handoff left the caller waiting silently. Added scripted on-entry questions for Symptom and Severity stages. Also made NameAge capture name then age in separate turns, and made Symptom, Severity, and yes/no choice turns force their specific registered tool after capturing caller input. `StopResponse` and `AgentSession.generate_reply(tool_choice="required", tools=[...])` were checked against installed LiveKit Agents 1.8.4. `py_compile`, a mocked name-to-age turn check, tool registration, and `git diff --check` passed; fresh browser call remains required. |
| 2026-10-25 | Booking confirmation repeated after spoken yes | Parser fixed; browser call pending | `RoutingAgent` accepted only exact strings such as `yes`, so common ASR output like `yes, please` was treated as unclear and triggered the clarification prompt. Added a normalized phrase parser for common affirmative and negative variants, leaving ambiguous responses on the clarification path. `py_compile`, `git diff --check`, and local examples for yes/no/unclear phrases passed. A fresh browser confirmation is still needed. |
| 2026-10-25 | Full conversation transcript recorder | Local recorder checks passed; live call pending | Added a per-call recorder using final `UserInputTranscribedEvent.transcript` values and assistant `ChatMessage.text_content`, with UTC timestamps and speaker labels. It writes JSON metadata/entries and a readable TXT transcript under `transcripts/` on AgentSession `close`; the caller participant disconnect initiates session shutdown, after which the final turn is drained. Local checks confirmed ordered caller/MAVIS entries, valid JSON/TXT output, whitespace filtering, and clean skip for zero entries. A full browser call, booking/emergency call, and real disconnect save were not run in this environment. Transcripts contain full conversation content and must remain synthetic demo data unless proper access control and encryption are added. |
| 2026-10-25 | Booking confirmation and final caller question | Source updated; full browser call pending | Booking confirmation now leads with a future-tense patient-portal reference, while the token is spoken as a temporary fallback until the Phase 5 portal exists. MAVIS then asks if the caller has another question, answers only from captured intake details using code, gives a voice-agent limitation for unsupported questions, thanks the caller, and ends the call. The full booking acceptance call was not run here. |
| 2026-10-26 | Speaches voice-path diagnosis and repair | TTS and STT round trip passed; browser call pending | Agent Python requests to `localhost:8000` timed out while `127.0.0.1` responded, so the agent fallback, both environment templates, and ignored local `.env` now use `127.0.0.1`. Speaches logs showed Kokoro loader `StopIteration` because its cache snapshot lacked `model.onnx`; redownloading completed the 177,464,787-byte file. A direct TTS request returned HTTP 200 with 75,820 WAV bytes. The first browser call then showed no completed STT event; Speaches logs showed Whisper could not create a lock under the root-owned volume and `model.bin` was absent. Corrected cache ownership; Whisper downloaded and loaded `model.bin`. Corrected both startup scripts to mount at `/home/ubuntu/.cache/huggingface`, copied both model caches into the persistent volume, recreated Speaches, and restarted the agent. A generated synthetic WAV was transcribed successfully as `This is a local synthetic voice track.` End-to-end browser intake remains unverified. |
When running verification, replace or append rows with actual results. Do not mark a check PASS based only on the existence of a script or source file.

## Update process for contributors

When a contributor completes or changes an item:

1. Update the relevant status and evidence above in the same change as the implementation.
2. Add a dated verification row when a check was actually run; include failures and limitations as well as passes.
3. Move unfinished tasks only when the implementation is present and reviewed. A planned feature or open pull request is not complete.
4. Keep Stage 4 items deferred until the user says `continue`.
5. Update the overall estimate when meaningful scope changes land, and state the basis for the new estimate.
