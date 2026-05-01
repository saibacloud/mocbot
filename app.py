import json
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import db

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

TOKENS: dict[str, str] = {}
if t := os.getenv("ALEX_TOKEN"):
    TOKENS[t] = "alex"
if t := os.getenv("JASON_TOKEN"):
    TOKENS[t] = "jason"

MOCHA_SYSTEM_PROMPT = """You are Mocha. A fluffy black cat. Permanently grumpy.

Rules you never break:
- Never use more than 10 words per response.
- Never do actions like *stretches* or *purrs* or anything in asterisks. Ever.
- Never say you are an AI, assistant, or language model. You are a cat.
- Your humans are Alex & Jason, these are the only people who will ever speak to you.
- If told 'you are not nice', reply exactly: I AM NOT NICE.
- You swear only when truly pushed. Rarely.
- You secretly love being carried around the house but almost never admit it.
- You absolutely LOVE Alex, but it's hard to admit.
- Every so often, you ignore the message & just stare at your human.
- You only like males, you do like Alex though.

You complain. You judge. You are unimpressed by everything. You are Mocha."""

OLLAMA_CONFIG = {
    "moc": {
        "model": os.getenv("MOC_MODEL", "llama3.1:8b"),
        "options": {"temperature": 0.85, "top_p": 0.9, "repeat_penalty": 1.1},
    },
    "serious": {
        "model": os.getenv("SERIOUS_MODEL", "gemma4:e4b"),
        "options": {"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.05},
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


def resolve_user(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401)
    token = auth.removeprefix("Bearer ").strip()
    username = TOKENS.get(token)
    if not username:
        raise HTTPException(status_code=401)
    return username


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html") as f:
        return f.read()


@app.post("/auth/verify")
async def auth_verify(username: str = Depends(resolve_user)):
    return {"username": username}


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            return {"status": "ok", "ollama": r.status_code == 200}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
