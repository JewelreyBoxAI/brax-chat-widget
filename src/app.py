import json
import logging
import os
import sys
import base64
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
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

# ─── ENV + LOGGING ───────────────────────────────────────────────────────────
load_dotenv()
logger = logging.getLogger("gym_bot")
logger.setLevel(logging.INFO)

# ─── PATHS & TEMPLATES ────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(ROOT, "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# ─── LOAD PROMPT CONFIG ───────────────────────────────────────────────────────
prompt_file = os.path.join(ROOT, "prompts", "prompt.json")
try:
    with open(prompt_file, "r", encoding="utf-8") as f:
        AGENT_ROLES = json.load(f)
except FileNotFoundError:
    logger.error(f"Prompt file not found at {prompt_file}")
    sys.exit("Prompt configuration is missing. Aborting startup.")

# ─── ENCODE AVATAR IMAGE ──────────────────────────────────────────────────────

img_path = os.path.join(ROOT, "images", "trump.png")
if os.path.exists(img_path):
    with open(img_path, "rb") as img:
        IMG_URI = "data:image/png;base64," + base64.b64encode(img.read()).decode()
else:
    logger.warning(f"Image not found at {img_path}, using fallback.")
    IMG_URI = "https://via.placeholder.com/60x60.png?text=Bot"

# ─── FASTAPI SETUP ───────────────────────────────────────────────────────────
app = FastAPI(title="The Gym Bot (Text Only)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
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

# ─── ROOT REDIRECT ───────────────────────────────────────────────────────────
@app.get("/")
async def root():
    """Redirect root URL to the widget"""
    return RedirectResponse(url="/widget")

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
        return JSONResponse(status_code=500, content={"error": "An internal error occurred. Please try again later."})

# ─── WIDGET ENDPOINT ─────────────────────────────────────────────────────────
@app.get("/widget", response_class=HTMLResponse)
async def widget(request: Request):
    """Render the chat widget UI"""
    return templates.TemplateResponse(
        "widget.html",
        {
            "request": request,
            "chat_url": f"{request.url.scheme}://{request.url.netloc}/chat",
            "img_uri": IMG_URI,
        },
    )

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
