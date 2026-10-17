"""LiveKit worker: connects synthetic web callers to local Speaches and Groq."""
import asyncio
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import openai, silero

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def get_caller_id(participant) -> str:
    """Prefer SIP's standard caller field, then the browser's synthetic value."""
    attrs = participant.attributes or {}
    return attrs.get("sip.phoneNumber") or attrs.get("caller_id") or "unknown caller"


def safety_gate(text: str) -> bool:
    """TODO Stage 4: add a reviewed rule-based safety check before the LLM."""
    return False


def log_latency(stage: str, at: datetime | None = None) -> None:
    """Append UTC event timestamps to the shared evaluation CSV."""
    path = ROOT / "eval" / "latency_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new:
            writer.writerow(["timestamp_utc", "stage"])
        writer.writerow([(at or datetime.now(timezone.utc)).isoformat(), stage])


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    caller_id = get_caller_id(participant)
    print(f"Synthetic caller connected: {caller_id}")

    base_url = os.getenv("SPEACHES_BASE_URL", "http://localhost:8000/v1")
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(
            model=os.getenv("STT_MODEL", "Systran/faster-whisper-small"),
            base_url=base_url,
            api_key="local-speaches",
        ),
        llm=openai.LLM(
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY", ""),
            reasoning_effort="low",
            max_completion_tokens=4096,
        ),
        tts=openai.TTS(
            model=os.getenv("TTS_MODEL", "speaches-ai/Kokoro-82M-v1.0-ONNX"),
            voice=os.getenv("TTS_VOICE", "af_heart"),
            base_url=base_url,
            api_key="local-speaches",
        ),
    )

    @session.on("user_state_changed")
    def on_user_state_changed(event) -> None:
        if getattr(event, "new_state", None) == "listening":
            log_latency("end_of_user_speech")

    @session.on("user_input_transcribed")
    def on_transcription(event) -> None:
        if getattr(event, "is_final", False):
            log_latency("stt_done")

    @session.on("conversation_item_added")
    def on_item(event) -> None:
        item = getattr(event, "item", None)
        if getattr(item, "role", "") == "assistant":
            # This event fires when the assistant message is added, not on token one.
            log_latency("llm_response_ready")

    @session.on("agent_state_changed")
    def on_agent_state(event) -> None:
        if getattr(event, "new_state", None) == "speaking":
            log_latency("tts_first_audio")

    prompt = (
        "You are MAVIS, an AI hospital intake assistant for a demo. Say you are an AI and this is a demo. "
        "Tell callers not to share real medical details. Use short sentences, one or two per turn. "
        "Ask about the main complaint, how long it has been happening, severity, and age. "
        "Do not diagnose or claim to provide medical care."
    )
    assistant = Agent(instructions=prompt)
    await session.start(agent=assistant, room=ctx.room)
    await session.say(
        "Hello, this is MAVIS, an AI assistant. This is a demo. How can I help you?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


