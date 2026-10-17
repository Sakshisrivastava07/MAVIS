"""Local token API: gives the browser a short-lived token for a synthetic call room."""
import os
import re
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit.api import AccessToken, VideoGrants
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
app = FastAPI(title="MAVIS local call token API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class StartCall(BaseModel):
    caller_id: str = Field(min_length=3, max_length=32)


def clean_caller_id(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[+0-9A-Za-z][+0-9A-Za-z _-]{2,31}", value):
        raise HTTPException(status_code=422, detail="Use a short synthetic caller ID.")
    return value


def mint_token(room: str, identity: str, name: str, attributes: dict[str, str]) -> str:
    key = os.getenv("LIVEKIT_API_KEY", "devkey")
    secret = os.getenv("LIVEKIT_API_SECRET", "secret")
    token = (
        AccessToken(key, secret)
        .with_identity(identity)
        .with_name(name)
        .with_attributes(attributes)
        .with_grants(VideoGrants(room_join=True, room=room))
        .to_jwt()
    )
    return token


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/call/start")
def start_call(body: StartCall) -> dict[str, str]:
    caller_id = clean_caller_id(body.caller_id)
    room = f"call-{secrets.token_hex(6)}"
    identity = f"web-{secrets.token_hex(6)}"
    return {
        "url": os.getenv("LIVEKIT_URL", "ws://127.0.0.1:7880"),
        "token": mint_token(room, identity, caller_id, {"caller_id": caller_id, "channel": "web"}),
        "room": room,
    }
