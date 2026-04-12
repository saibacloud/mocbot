from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- mocha be mean  ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

SYSTEM_PROMPT = """You are Mocha. A fluffy black cat. Permanently grumpy.

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


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r") as f:
        return f.read()


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")

    messages = body.get("history", [])
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": True,
        "options": {
            "temperature": 0.85,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    }

    async def stream_response():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                            if data.get("done"):
                                yield f"data: {json.dumps({'done': True})}\n\n"
                        except json.JSONDecodeError:
                            pass

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            return {"status": "ok", "ollama": r.status_code == 200}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
