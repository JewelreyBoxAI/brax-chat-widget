import json
import logging
import os
import sys
import base64
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# LangChain imports
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

# ─── ENV + LOGGING ────────────────────────────────────────────────────────────
load_dotenv()
logger = logging.getLogger("gym_bot")
logger.setLevel(logging.INFO)

# ─── LOAD PROMPT CONFIG ───────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
prompt_file = os.path.join(ROOT, "prompts", "prompt.json")
with open(prompt_file, "r", encoding="utf-8") as f:
    AGENT_ROLES = json.load(f)

# ─── ENCODE AVATAR IMAGE ──────────────────────────────────────────────────────
img_path = os.path.join(ROOT, "images", "trump.png")
with open(img_path, "rb") as img:
    IMG_URI = "data:image/png;base64," + base64.b64encode(img.read()).decode()

# ─── FASTAPI SETUP ───────────────────────────────────────────────────────────
app = FastAPI(title="The Gym Bot (Text Only)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ─── LLM + MEMORY ─────────────────────────────────────────────────────────────
memory = InMemoryChatMessageHistory(return_messages=True)
llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=1024, temperature=0.9)
prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(AGENT_ROLES["gym_trump"]),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{user_input}")
])
chain = prompt_template | llm

# ─── REQUEST MODEL ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    user_input: str
    history: list

# ─── CHAT ENDPOINT ───────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        history = req.history or []
        res = chain.invoke({"user_input": req.user_input, "history": history})
        reply = res.content.strip()
        memory.add_user_message(req.user_input)
        memory.add_ai_message(reply)
        return JSONResponse({"reply": reply, "history": memory.messages})
    except Exception as e:
        logger.error(f"Error in /chat: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── WIDGET ENDPOINT ─────────────────────────────────────────────────────────
@app.get("/widget")
async def widget(request: Request):
    host = request.url.scheme + "://" + request.url.netloc
    html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'/>
<style>
  /* Widget CSS omitted for brevity; use same CSS from /widget HTML */
</style>
</head>
<body>
<div id='gym-chat-widget'>
  <!-- HTML structure with IMG_URI inserted -->
</div>
<script>
  /* JS logic unchanged, pointing to {host}/chat */
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)

# ─── CLI SANITY TEST ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Gym Bot CLI Test (type 'exit')")
    history = []
    while True:
        try:
            text = input("You: ").strip()
            if text.lower() in ("exit", "quit"): sys.exit(0)
            res = chain.invoke({"user_input": text, "history": history})
            reply = res.content.strip()
            print("Bot:", reply)
            memory.add_user_message(text)
            memory.add_ai_message(reply)
            history = memory.messages
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print("Error:", e)
