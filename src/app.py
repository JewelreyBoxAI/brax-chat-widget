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
from typing import Optional
from dotenv import load_dotenv

# LangChain imports
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage
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

img_path = os.path.join(ROOT, "images", "brax_avatar.png")
if os.path.exists(img_path):
    with open(img_path, "rb") as img:
        IMG_URI = "data:image/png;base64," + base64.b64encode(img.read()).decode()
else:
    logger.warning(f"Image not found at {img_path}, using fallback.")
    IMG_URI = "https://via.placeholder.com/60x60.png?text=Brax"

# ─── FASTAPI SETUP ───────────────────────────────────────────────────────────

app = FastAPI(title="Brax Fine Jewelers AI Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ─── LLM + MEMORY ─────────────────────────────────────────────────────────────

memory = InMemoryChatMessageHistory(return_messages=True)
llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=1024, temperature=0.9)
prompt_text = " ".join(AGENT_ROLES["brax_jeweler"]) if isinstance(AGENT_ROLES["brax_jeweler"], list) else AGENT_ROLES["brax_jeweler"]
prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(prompt_text),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{user_input}")
])
chain = prompt_template | llm

# ─── REQUEST MODEL ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_input: str
    history: list

# ─── JEWELRY-SPECIFIC MODELS ──────────────────────────────────────────────────

class JewelryRequest(BaseModel):
    occasion: str  # engagement, anniversary, birthday, etc.
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    style_preference: Optional[str] = None  # classic, modern, vintage
    metal_preference: Optional[str] = None  # gold, platinum, silver
    stone_preference: Optional[str] = None  # diamond, sapphire, emerald

class AppointmentRequest(BaseModel):
    customer_name: str
    email: str
    phone: str
    preferred_date: str
    consultation_type: str  # custom_design, appraisal, selection
    message: Optional[str] = None

# ─── ROOT REDIRECT ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Redirect root URL to the widget"""
    return RedirectResponse(url="/widget")

# ─── CHAT ENDPOINT ───────────────────────────────────────────────────────────

def serialize_messages(messages: list[BaseMessage]):
    return [{"role": msg.type, "content": msg.content} for msg in messages]

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        history = req.history or []
        res = chain.invoke({"user_input": req.user_input, "history": history})
        reply = res.content.strip()
        memory.add_user_message(req.user_input)
        memory.add_ai_message(reply)
        return JSONResponse({
            "reply": reply,
            "history": serialize_messages(memory.messages)
        })
    except Exception as e:
        logger.error(f"Error in /chat: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred. Please try again later."}
        )

# ─── CLEAR CHAT ENDPOINT ──────────────────────────────────────────────────────

@app.post("/clear_chat")
async def clear_chat():
    """
    Clear in-memory chat history for all users (global reset).
    Note: This affects all sessions since memory is global.
    """
    try:
        memory.clear()
        return JSONResponse({"status": "ok", "message": "Chat history cleared."})
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to clear chat history."}
        )

# ─── JEWELRY-SPECIFIC ENDPOINTS ───────────────────────────────────────────────

@app.post("/jewelry/recommend")
async def recommend_jewelry(request: JewelryRequest):
    """Recommend jewelry pieces based on occasion, budget, and style preferences"""
    try:
        # This would integrate with Brax inventory system
        recommendations = {
            "occasion": request.occasion,
            "recommendations": [
                {
                    "id": "BR001",
                    "name": "Classic Solitaire Engagement Ring",
                    "price": "$2,500 - $15,000",
                    "description": "Timeless elegance with certified diamonds",
                    "image_url": "/images/solitaire-ring.jpg"
                },
                {
                    "id": "BR002", 
                    "name": "Vintage Art Deco Collection",
                    "price": "$1,800 - $8,500",
                    "description": "Inspired by 1920s glamour with intricate details",
                    "image_url": "/images/art-deco-collection.jpg"
                }
            ]
        }
        return JSONResponse(recommendations)
    except Exception as e:
        logger.error(f"Error in jewelry recommendations: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to process jewelry recommendation request."}
        )

@app.post("/appointment/schedule")
async def schedule_consultation(request: AppointmentRequest):
    """Schedule an in-person jewelry consultation"""
    try:
        # This would integrate with Brax appointment system
        appointment_data = {
            "appointment_id": f"BRAX-{request.customer_name[:3].upper()}-001",
            "customer": request.customer_name,
            "email": request.email,
            "phone": request.phone,
            "date": request.preferred_date,
            "type": request.consultation_type,
            "status": "pending_confirmation",
            "message": "Thank you for scheduling with Brax Fine Jewelers. We'll contact you within 24 hours to confirm your appointment."
        }
        return JSONResponse(appointment_data)
    except Exception as e:
        logger.error(f"Error scheduling appointment: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to schedule appointment. Please call (949) 250-9949."}
        )

@app.get("/inventory/search")
async def search_inventory(query: str, budget_min: Optional[float] = None, budget_max: Optional[float] = None):
    """Search Brax inventory based on criteria"""
    try:
        # This would integrate with Brax inventory database
        search_results = {
            "query": query,
            "budget_range": f"${budget_min or 0} - ${budget_max or 'No limit'}",
            "results": [
                {
                    "id": "BR101",
                    "name": f"Diamond {query.title()} Collection",
                    "price_range": "$1,200 - $12,000",
                    "available": True,
                    "description": f"Exquisite {query} pieces featuring certified diamonds and precious metals"
                }
            ],
            "total_count": 1
        }
        return JSONResponse(search_results)
    except Exception as e:
        logger.error(f"Error searching inventory: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to search inventory at this time."}
        )

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
    print("Brax Fine Jewelers AI Assistant CLI Test (type 'exit')")
    history = []
    while True:
        try:
            text = input("You: ").strip()
            if text.lower() in ("exit", "quit"): sys.exit(0)
            res = chain.invoke({"user_input": text, "history": history})
            reply = res.content.strip()
            print("Elena:", reply)
            memory.add_user_message(text)
            memory.add_ai_message(reply)
            history = memory.messages
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print("Error:", e)
