import inspect
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


@app.get("/sessions")
async def list_sessions(username: str = Depends(resolve_user)):
    return await db.list_sessions(username)


@app.post("/sessions", status_code=201)
async def create_session(request: Request, username: str = Depends(resolve_user)):
    body = await request.json()
    mode = body.get("mode", "moc")
    if mode not in ("moc", "serious"):
        raise HTTPException(status_code=400, detail="mode must be 'moc' or 'serious'")
    return await db.create_session(username, mode)


@app.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, username: str = Depends(resolve_user)):
    if not await db.delete_session(session_id, username):
        raise HTTPException(status_code=404)


@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, username: str = Depends(resolve_user)):
    if not await db.get_session(session_id, username):
        raise HTTPException(status_code=404)
    return await db.get_messages(session_id)


@app.get("/context")
async def get_context(username: str = Depends(resolve_user)):
    return {"context": await db.get_context(username)}


@app.put("/context")
async def set_context(request: Request, username: str = Depends(resolve_user)):
    body = await request.json()
    await db.set_context(username, body.get("context", ""))
    return {"ok": True}


async def _generate_title(user_msg: str, assistant_msg: str, config: dict) -> str:
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": f"User: {user_msg}\nAssistant: {assistant_msg}"},
            {"role": "user", "content": "Summarise this conversation as a chat title in 4-5 words. Reply with only the title, no punctuation."},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
            return r.json().get("message", {}).get("content", "").strip()[:60]
    except Exception:
        return ""


@app.post("/sessions/{session_id}/chat")
async def chat(session_id: str, request: Request, username: str = Depends(resolve_user)):
    session = await db.get_session(session_id, username)
    if not session:
        raise HTTPException(status_code=404)

    body = await request.json()
    user_message = body.get("message", "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    mode = session["mode"]
    config = OLLAMA_CONFIG[mode]
    history = await db.get_messages(session_id)
    is_first = len(history) == 0

    await db.add_message(session_id, "user", user_message)

    ollama_messages = []
    if mode == "moc":
        ollama_messages.append({"role": "system", "content": MOCHA_SYSTEM_PROMPT})
    else:
        context = await db.get_context(username)
        if context:
            ollama_messages.append({"role": "system", "content": context})

    for msg in history:
        ollama_messages.append({"role": msg["role"], "content": msg["content"]})
    ollama_messages.append({"role": "user", "content": user_message})

    payload = {
        "model": config["model"],
        "messages": ollama_messages,
        "stream": True,
        "options": config["options"],
    }

    async def stream_response():
        full_reply = ""
        async with httpx.AsyncClient(timeout=180.0) as client:
            stream_ctx = client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=payload)
            if inspect.isawaitable(stream_ctx):
                stream_ctx = await stream_ctx
            async with stream_ctx as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if chunk := data.get("message", {}).get("content"):
                            full_reply += chunk
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        if data.get("done"):
                            yield f"data: {json.dumps({'done': True})}\n\n"
                    except json.JSONDecodeError:
                        pass

        await db.add_message(session_id, "assistant", full_reply)

        if is_first and full_reply:
            title = await _generate_title(user_message, full_reply, config)
            if title:
                await db.set_session_title(session_id, username, title)
                yield f"data: {json.dumps({'title': title})}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")
