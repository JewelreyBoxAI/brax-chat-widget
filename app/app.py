import json
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables import RunnableLambda

# ─── ENV + LOGGING ────────────────────────────────────────────────────────────
load_dotenv()
logger = logging.getLogger("gym_bot")
logger.setLevel(logging.INFO)

# ─── PROMPT CONFIG ────────────────────────────────────────────────────────────
with open("prompts/prompt.json", "r", encoding="utf-8") as f:
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
memory = ConversationBufferMemory(return_messages=True)
llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=1024, temperature=0.9)

class AgentWrapper(RunnableLambda):
    def __init__(self, chain):
        super().__init__(lambda x: chain.invoke(x))
        self.chain = chain

def build_agent(agent_type="gym_trump") -> AgentWrapper:
    system_msg = AGENT_ROLES[agent_type]
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_msg),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{user_input}")
    ])
    chain = prompt | llm
    return AgentWrapper(chain=chain)

agent = build_agent()

# ─── REQUEST MODEL ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    user_input: str
    history: list

# ─── CHAT ROUTE ───────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        mem_vars = memory.load_memory_variables({})
        mem_vars["history"] = req.history

        output = agent.invoke({
            "user_input": req.user_input,
            "history": mem_vars["history"]
        })
        reply = output.content.strip()

        memory.save_context(
            {"user": req.user_input},
            {"assistant": reply}
        )

        return JSONResponse({
            "reply": reply,
            "history": memory.load_memory_variables({})["history"]
        })

    except Exception as e:
        logger.error(f"☠️ Chat error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── HEALTHCHECK ROUTE ────────────────────────────────────────────────────────
@app.get("/")
async def healthcheck():
    return {"status": "ok", "message": "The Gym Bot is running 🏋️"}
