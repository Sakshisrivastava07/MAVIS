# MAVIS local demo architecture

```mermaid
flowchart LR
  Browser[Virtual phone<br/>localhost:5500] -->|token request| API[FastAPI<br/>localhost:8001]
  API -->|short-lived room token| Browser
  Browser <-->|WebRTC audio| LK[LiveKit dev server<br/>localhost:7880]
  Agent[Python LiveKit Agent] <-->|WebRTC audio| LK
  Agent -->|STT and TTS| Speech[Speaches CPU<br/>localhost:8000]
  Agent -->|chat completion| Groq[Groq free-tier API]
```

The browser calls the local API to receive a temporary room token with a fake caller ID. Both browser and agent join the self-hosted LiveKit room. The agent sends captured audio to Speaches for transcription, asks Groq for a short text reply, then sends it to Speaches for speech. Only the LLM request leaves the computer. All caller data in this prototype must be invented.
