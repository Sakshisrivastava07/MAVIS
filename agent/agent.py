"""LiveKit worker for the local MAVIS demo, with code-controlled intake handoffs."""

import csv
import itertools
import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    StopResponse,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import openai, silero

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
logger = logging.getLogger(__name__)

# This demo represents only the configured sample hospital.
HOSPITAL_NAME = "Sunrise General Hospital"

DEPARTMENTS = {
    "Cardiology": {
        "keywords": ["chest pain", "heart", "palpitation", "blood pressure"],
        "doctors": ["Dr. Anita Rao", "Dr. Imran Shaikh"],
    },
    "Orthopedics": {
        "keywords": ["fracture", "joint pain", "back pain", "knee", "bone", "sprain"],
        "doctors": ["Dr. Priya Nair", "Dr. Karthik Menon"],
    },
    "Pediatrics": {
        "keywords": ["child", "baby", "infant", "kid", "toddler"],
        "doctors": ["Dr. Meera Iyer", "Dr. Sanjay Gupta"],
    },
    "ENT": {
        "keywords": ["ear", "nose", "throat", "sinus", "hearing"],
        "doctors": ["Dr. Farah Khan"],
    },
    "Dermatology": {
        "keywords": ["skin", "rash", "itching", "acne"],
        "doctors": ["Dr. Leela Krishnan"],
    },
    "Gynecology": {
        "keywords": ["pregnan", "period", "menstrual"],
        "doctors": ["Dr. Ritu Sharma"],
    },
    "Neurology": {
        "keywords": ["headache", "migraine", "seizure", "numbness", "dizz"],
        "doctors": ["Dr. Arvind Pillai"],
    },
    "Gastroenterology": {
        "keywords": ["stomach", "abdomen", "vomit", "diarrh", "nausea"],
        "doctors": ["Dr. Nisha Verma"],
    },
    "Psychiatry": {
        "keywords": ["anxious", "depress", "stress", "sleep problem", "panic"],
        "doctors": ["Dr. Omar Siddiqui"],
    },
    "General Medicine": {
        "keywords": [],
        "doctors": ["Dr. Varun Kapoor", "Dr. Sheila Thomas"],
    },
}

# Pattern-level red flags for this demo only; this is not medical triage.
EMERGENCY_KEYWORDS = [
    "crushing chest pain",
    "can't breathe",
    "cannot breathe",
    "severe bleeding",
    "heavy bleeding",
    "unconscious",
    "unresponsive",
    "stroke",
    "face drooping",
    "slurred speech",
    "suicidal",
    "want to die",
    "severe burns",
    "choking",
    "seizure right now",
]


@dataclass
class IntakeData:
    """Per-call values shared by all agents in the handoff chain."""

    name: str = ""
    age: str = ""
    symptom_description: str = ""
    severity: str = ""
    history: str = ""
    department: str = ""


def get_caller_id(participant) -> str:
    """Prefer SIP's standard caller field, then the browser's synthetic value."""
    attrs = participant.attributes or {}
    return attrs.get("sip.phoneNumber") or attrs.get("caller_id") or "unknown caller"


def safety_gate(text: str) -> bool:
    """Return whether a configured red-flag phrase occurs in demo text."""
    lowered = text.lower()
    return any(flag in lowered for flag in EMERGENCY_KEYWORDS)


def route_department(symptom_text: str) -> str:
    """Select a department with deterministic keyword matching."""
    lowered = symptom_text.lower()
    for department, info in DEPARTMENTS.items():
        if department == "General Medicine":
            continue
        if any(keyword in lowered for keyword in info["keywords"]):
            return department
    return "General Medicine"


def parse_booking_choice(text: str) -> bool | None:
    """Parse common spoken yes/no variants; return None for unclear answers."""
    answer = re.sub(r"[^a-z0-9']+", " ", text.lower().replace("’", "'")).strip()
    answer = re.sub(r"\s+", " ", answer)
    if not answer:
        return None

    negative_phrases = (
        "not now",
        "not interested",
        "not today",
        "rather not",
        "don't want",
        "do not want",
        "would not",
        "wouldn't",
        "no thanks",
        "no thank you",
    )
    if any(phrase in answer for phrase in negative_phrases):
        return False
    if answer == "no problem":
        return True
    if re.match(r"^(no|nope|nah|negative)\b", answer):
        return False

    affirmative_starts = (
        "yes", "yeah", "yep", "yup", "sure", "okay", "ok", "absolutely",
        "definitely", "please do", "go ahead", "book it", "book me", "i would",
        "i'd", "i want", "i'd like", "that works", "sounds good", "that's fine",
        "thats fine",
    )
    if any(answer == phrase or answer.startswith(phrase + " ") for phrase in affirmative_starts):
        return True
    return None


# Demo-only, in-memory appointment data. This does not connect to a scheduler.
_booking_lock = threading.Lock()
_token_counter = itertools.count(1)
_doctor_cycles = {
    dept: itertools.cycle(info["doctors"]) for dept, info in DEPARTMENTS.items()
}
_department_next_slot: dict[str, datetime] = {}


def book_slot(department: str) -> dict[str, str]:
    """Create a synthetic token and assign the next in-memory demo slot."""
    with _booking_lock:
        token_number = next(_token_counter)
        token = f"{department[:2].upper()}{token_number:04d}"
        doctor = next(_doctor_cycles[department])
        now = datetime.now(timezone.utc)
        slot_start = _department_next_slot.get(department, now + timedelta(minutes=20))
        if slot_start < now:
            slot_start = now + timedelta(minutes=20)
        _department_next_slot[department] = slot_start + timedelta(minutes=15)
        arrive_by = slot_start - timedelta(minutes=10)
        return {
            "token": token,
            "doctor": doctor,
            "department": department,
            "appointment_time": slot_start.strftime("%I:%M %p"),
            "arrive_by": arrive_by.strftime("%I:%M %p"),
        }


def log_event(stage: str, at: datetime | None = None) -> None:
    """Append a UTC event to the shared latency/event CSV."""
    path = ROOT / "eval" / "latency_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if new:
            writer.writerow(["timestamp_utc", "stage"])
        writer.writerow([(at or datetime.now(timezone.utc)).isoformat(), stage])


class TranscriptRecorder:
    """Collect one call's timestamped transcript and write JSON plus plain text."""

    # Transcripts contain full conversation content: synthetic demo data only, not secure real-patient storage without access control/encryption.
    def __init__(self, header: dict[str, str]) -> None:
        self.header = header
        self.entries: list[dict[str, str]] = []

    def add(self, speaker: str, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        self.entries.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "speaker": speaker,
                "text": cleaned,
            }
        )

    def write(self, path: Path) -> tuple[Path, Path] | None:
        if not self.entries:
            return None

        path.parent.mkdir(parents=True, exist_ok=True)
        base_path = path.with_suffix("")
        json_path = base_path.with_suffix(".json")
        text_path = base_path.with_suffix(".txt")
        payload = {"header": self.header, "entries": self.entries}
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        lines = [
            "MAVIS call transcript",
            f"Hospital: {self.header['hospital']}",
            f"Caller: {self.header['caller_id']}",
            f"Room: {self.header['room_name']}",
            f"Started: {self.header['call_started_at']}",
            "----------------------------------------",
        ]
        for entry in self.entries:
            timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M:%S")
            lines.append(f"[{timestamp}] {entry['speaker'].upper()}: {entry['text']}")
        text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return json_path, text_path


class NameAgeAgent(Agent):
    """Collect only the caller's full name and age."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Collect only the caller's full name and then age. Ask one at a time. "
                "If they give a different answer, politely ask for the full name or age "
                "that is still missing. Do not ask about symptoms or anything else. "
                "When both are known, call record_name_age with the caller's answers."
            )
        )

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Capture name and age in separate turns and speak the age prompt in code."""
        answer = (new_message.raw_text_content or "").strip()
        if not answer:
            return

        data = self.session.userdata
        if not data.name:
            data.name = answer
            log_event("caller_name_received")
            prompt = self.session.say(
                "Thank you. How old are you?",
                allow_interruptions=False,
            )
            await prompt.wait_for_playout()
            raise StopResponse()

        if not data.age:
            data.age = answer
            log_event("caller_age_received")
            self.session.generate_reply(
                user_input=new_message,
                instructions=(
                    "Call record_name_age now with these exact captured values: "
                    f"name={data.name!r}, age={data.age!r}. Do not speak additional text."
                ),
                tool_choice="required",
                tools=["record_name_age"],
            )
            raise StopResponse()

    @function_tool()
    async def record_name_age(
        self, context: RunContext[IntakeData], name: str, age: str
    ) -> Agent:
        """Save name and age, then hand off to the symptom stage."""
        if not context.userdata.name:
            context.userdata.name = name.strip()
        if not context.userdata.age:
            context.userdata.age = age.strip()
        if not context.userdata.name or not context.userdata.age:
            raise ValueError("Name and age must both be captured before handoff.")
        log_event("handoff_name_age_to_symptom")
        return SymptomAgent()


class SymptomAgent(Agent):
    """Collect the caller's symptom description and make the code-based branch."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Ask only what problem or symptom brought the caller in today, in their "
                "own words. Do not ask about severity, history, age, or anything else. "
                "When they answer, call record_symptom with their description."
            )
        )

    async def on_enter(self) -> None:
        prompt = self.session.say(
            "What problem or symptom brought you in today? Please describe it in your own words.",
            allow_interruptions=False,
        )
        await prompt.wait_for_playout()

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Capture the actual symptom turn and require the branch tool to run."""
        answer = (new_message.raw_text_content or "").strip()
        if not answer:
            return
        self.session.userdata.symptom_description = answer
        log_event("caller_symptom_received")
        self.session.generate_reply(
            user_input=new_message,
            instructions=(
                "Call record_symptom now using the caller's symptom from this turn. "
                "Do not make an urgency decision and do not speak additional text."
            ),
            tool_choice="required",
            tools=["record_symptom"],
        )
        raise StopResponse()

    @function_tool()
    async def record_symptom(
        self, context: RunContext[IntakeData], symptom_description: str
    ) -> Agent:
        """Save the symptom and choose the next agent using the Python safety gate."""
        symptom = context.userdata.symptom_description or symptom_description.strip()
        context.userdata.symptom_description = symptom
        if safety_gate(symptom):
            log_event("handoff_symptom_to_emergency")
            return EmergencyAgent()
        log_event("handoff_symptom_to_severity")
        return SeverityAgent()


class EmergencyAgent(Agent):
    """Give the truthful demo-only urgent response and end the call."""

    def __init__(self) -> None:
        super().__init__(instructions="Do not generate or ask anything; this stage is scripted.")

    async def on_enter(self) -> None:
        log_event("EMERGENCY_DETECTED")
        speech = self.session.say(
            "This sounds urgent. In the full system this would immediately connect you "
            "to a nurse. For this demo, please call emergency services or hospital "
            "reception directly.",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        self.session.shutdown(drain=True)


class SeverityAgent(Agent):
    """Collect severity and one brief duration/history detail."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Ask the caller to rate severity from 1 to 10. Then ask one brief "
                "follow-up history question, such as how long it has been happening. "
                "Ask nothing else. When both answers are known, call "
                "record_severity_history with them."
            )
        )

    async def on_enter(self) -> None:
        prompt = self.session.say(
            "On a scale from 1 to 10, how severe does it feel?",
            allow_interruptions=False,
        )
        await prompt.wait_for_playout()

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Ask severity and duration separately, then require the handoff tool."""
        answer = (new_message.raw_text_content or "").strip()
        if not answer:
            return

        data = self.session.userdata
        if not data.severity:
            data.severity = answer
            log_event("caller_severity_received")
            prompt = self.session.say(
                "How long has this been happening?",
                allow_interruptions=False,
            )
            await prompt.wait_for_playout()
            raise StopResponse()

        if not data.history:
            data.history = answer
            log_event("caller_history_received")
            self.session.generate_reply(
                user_input=new_message,
                instructions=(
                    "Call record_severity_history now with these exact captured values: "
                    f"severity={data.severity!r}, history={data.history!r}. "
                    "Do not speak additional text."
                ),
                tool_choice="required",
                tools=["record_severity_history"],
            )
            raise StopResponse()

    @function_tool()
    async def record_severity_history(
        self, context: RunContext[IntakeData], severity: str, history: str
    ) -> Agent:
        """Save severity/history and hand off to the deterministic routing stage."""
        if not context.userdata.severity:
            context.userdata.severity = severity.strip()
        if not context.userdata.history:
            context.userdata.history = history.strip()
        log_event("handoff_severity_to_routing")
        return RoutingAgent()


class RoutingAgent(Agent):
    """Announce the code-selected department and ask the fixed booking question."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Use only the department selected by the code and already announced. "
                "Ask exactly: 'Would you like me to book an appointment for you?' "
                "Do not ask about time, availability, or scheduling preferences. "
                "Call confirm_booking_choice with true only for an explicit yes and "
                "false only for an explicit no."
            )
        )

    async def on_enter(self) -> None:
        data = self.session.userdata
        data.department = route_department(data.symptom_description)
        log_event("department_routed")
        speech = self.session.say(
            f"Based on what you shared, the {data.department} department may be a fit. "
            "Would you like me to book an appointment for you?",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Resolve a clear yes/no in code and require the choice tool."""
        wants_booking = parse_booking_choice(new_message.raw_text_content or "")
        if wants_booking is None:
            prompt = self.session.say(
                "Please answer yes or no. Would you like me to book an appointment for you?",
                allow_interruptions=False,
            )
            await prompt.wait_for_playout()
            raise StopResponse()

        self.session.generate_reply(
            user_input=new_message,
            instructions=(
                "Call confirm_booking_choice using wants_booking="
                f"{str(wants_booking).lower()}. Do not speak additional text."
            ),
            tool_choice="required",
            tools=["confirm_booking_choice"],
        )
        raise StopResponse()

    @function_tool()
    async def confirm_booking_choice(
        self, context: RunContext[IntakeData], wants_booking: bool
    ) -> Agent | None:
        """Hand off to booking on yes; otherwise close the call politely."""
        if wants_booking:
            log_event("booking_confirmed")
            return BookingAgent()
        log_event("booking_declined")
        speech = context.session.say(
            "All right. Thank you for calling the MAVIS demo. Goodbye.",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        context.session.shutdown(drain=True)
        return None


class BookingAgent(Agent):
    """Create a synthetic booking, offer one grounded follow-up, then end."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Do not invent booking or caller details. The booking confirmation and "
                "one final follow-up response are scripted in code."
            )
        )
        self.booking_result: dict[str, str] | None = None

    def book_appointment(self) -> dict[str, str]:
        """Create a synthetic appointment using the deterministic Python logic."""
        data = self.session.userdata
        result = book_slot(data.department)
        log_event(f"BOOKED {result['token']} dept={data.department}")
        return result

    async def on_enter(self) -> None:
        result = self.book_appointment()
        self.booking_result = result
        # Temporary recovery fallback: remove the spoken token once the Phase 5 portal can look bookings up.
        speech = self.session.say(
            f"Your appointment is booked. In the full system, you'd check your appointment "
            f"details, including your department, doctor, and time slot, on the hospital's "
            f"patient portal. This is a demo, so there's no live portal yet — for now, "
            f"your reference token is {result['token']}, so you have a way to find this "
            f"booking until the portal exists.",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        question = self.session.say(
            "Is there anything else you'd like to ask about the details you shared?",
            allow_interruptions=False,
        )
        await question.wait_for_playout()

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        """Answer only a question about captured intake details, then close politely."""
        question = (new_message.raw_text_content or "").lower()
        data = self.session.userdata
        detail = None
        if any(word in question for word in ("my name", "what name", "name did", "who am i")):
            detail = f"You told me your name is {data.name}."
        elif any(word in question for word in ("my age", "how old", "age did")):
            detail = f"You told me you are {data.age} years old."
        elif any(word in question for word in ("symptom", "problem", "what did i say", "what brought")):
            detail = f"You described: {data.symptom_description}."
        elif any(word in question for word in ("severity", "scale", "rating")):
            detail = f"You rated the severity as {data.severity} out of 10."
        elif any(word in question for word in ("how long", "history", "duration")):
            detail = f"You said this has been happening for: {data.history}."

        if detail is None:
            response = (
                "I'm a voice agent, so I can only help with the details you shared "
                "during this demo. "
            )
        else:
            response = detail + " "
        speech = self.session.say(
            response + "Thank you. I hope you have a good day.",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        self.session.shutdown(drain=True)
        raise StopResponse()


async def entrypoint(ctx: JobContext) -> None:
    """Connect one browser caller, preserve provider wiring, and start the flow."""
    print("MAVIS worker received a job; connecting to local LiveKit.", flush=True)
    log_event("worker_job_received")
    # Bypass HTTP proxies only for the local LiveKit socket.
    proxy_env = {}
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if name in os.environ:
            proxy_env[name] = os.environ.pop(name)
    try:
        await ctx.connect()
    finally:
        os.environ.update(proxy_env)
    print("MAVIS worker connected to LiveKit; waiting for browser caller.", flush=True)
    log_event("worker_connected_to_livekit")

    participant = await ctx.wait_for_participant()
    caller_id = get_caller_id(participant)
    print(f"Synthetic caller connected: {caller_id}", flush=True)
    log_event("browser_participant_joined")

    call_started_at = datetime.now(timezone.utc)
    header = {
        "call_started_at": call_started_at.isoformat(),
        "caller_id": caller_id,
        "room_name": ctx.room.name,
        "hospital": HOSPITAL_NAME,
    }
    recorder = TranscriptRecorder(header)
    safe_caller_id = re.sub(r"[^A-Za-z0-9._-]+", "-", caller_id).strip("-") or "unknown-caller"
    call_stamp = call_started_at.strftime("%Y-%m-%dT%H-%M-%S-%f")
    transcript_base = ROOT / "transcripts" / f"{call_stamp}_{safe_caller_id}"

    def save_transcript(event) -> None:
        try:
            saved_paths = recorder.write(transcript_base)
            if saved_paths is None:
                return
            log_event(f"TRANSCRIPT_SAVED {saved_paths[0]}")
            print(f"MAVIS transcript saved: {saved_paths[0]} and {saved_paths[1]}", flush=True)
        except Exception:
            logger.exception("Could not save the MAVIS call transcript")

    base_url = os.getenv("SPEACHES_BASE_URL", "http://127.0.0.1:8000/v1")
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
        userdata=IntakeData(),
    )

    @session.on("user_state_changed")
    def on_user_state_changed(event) -> None:
        if getattr(event, "new_state", None) == "listening":
            log_event("end_of_user_speech")

    @session.on("user_input_transcribed")
    def on_transcription(event) -> None:
        if getattr(event, "is_final", False):
            log_event("stt_done")
            recorder.add("caller", getattr(event, "transcript", ""))

    @session.on("conversation_item_added")
    def on_item(event) -> None:
        item = getattr(event, "item", None)
        if getattr(item, "role", "") == "assistant":
            log_event("llm_response_ready")
            text = getattr(item, "text_content", None) or getattr(
                item, "raw_text_content", ""
            )
            recorder.add("mavis", text or "")

    @session.on("agent_state_changed")
    def on_agent_state(event) -> None:
        if getattr(event, "new_state", None) == "speaking":
            log_event("tts_first_audio")

    # Session close runs after active speech and the final STT turn have been drained.
    session.on("close", save_transcript)

    def on_participant_disconnected(disconnected_participant) -> None:
        if disconnected_participant.identity == participant.identity:
            log_event("caller_disconnected")
            session.shutdown(drain=True)

    ctx.room.on("participant_disconnected", on_participant_disconnected)

    print("Starting MAVIS audio session with NameAgeAgent.", flush=True)
    await session.start(agent=NameAgeAgent(), room=ctx.room)
    print("MAVIS audio session started; sending scripted greeting.", flush=True)
    log_event("agent_session_started")
    greeting = session.say(
        "Hello, this is MAVIS, an AI assistant for a demo. Please do not share real "
        "medical details. What is your full name?",
        allow_interruptions=False,
    )
    await greeting.wait_for_playout()
    print("MAVIS greeting playout completed.", flush=True)
    log_event("greeting_playout_completed")


if __name__ == "__main__":
    # Keep local LiveKit traffic out of the configured HTTP proxy.
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, http_proxy=None))
