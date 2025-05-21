import json
import logging
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

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

# ─── PROMPT CONFIG ────────────────────────────────────────────────────────────
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "prompt.json")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    AGENT_ROLES = json.load(f)

# ─── FASTAPI INIT ─────────────────────────────────────────────────────────────
app = FastAPI(title="The Gym Bot (Text Only)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# ─── LLM + MEMORY ─────────────────────────────────────────────────────────────
memory = InMemoryChatMessageHistory(return_messages=True)
llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=1024, temperature=0.9)

# Prepare prompt chain once
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

# ─── CHAT ROUTE ───────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        history = req.history or []
        # Invoke chain directly
        result = chain.invoke({"user_input": req.user_input, "history": history})
        reply = result.content.strip()
        # Update memory
        memory.add_user_message(req.user_input)
        memory.add_ai_message(reply)
        return JSONResponse({"reply": reply, "history": memory.messages})
    except Exception as e:
        logger.error(f"☠️ Chat error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── CLI SANITY TEST ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n⚡ Gym Bot CLI Test (type 'exit' to quit)\n")
    history = []
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("⚡ Bye.")
                sys.exit(0)
            result = chain.invoke({"user_input": user_input, "history": history})
            reply = result.content.strip()
            print("Bot:", reply)
            memory.add_user_message(user_input)
            memory.add_ai_message(reply)
            history = memory.messages
        except KeyboardInterrupt:
            print("\n⚡ Interrupted. Exiting.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"☠️ CLI error: {e}", exc_info=True)
            print("Error:", e)
