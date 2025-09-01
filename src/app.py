import json
import logging
import os
import sys
import base64
import uuid
import re
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, field_validator, Field
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# LangChain (canonical)
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

# ─── ENV + LOGGING ───────────────────────────────────────────────────────────

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("brax_jeweler")

# Validate critical environment variables at startup
REQUIRED_ENV_VARS = {
    'OPENAI_API_KEY': 'OpenAI API key is required for LLM functionality'
}

missing_vars = []
for var, description in REQUIRED_ENV_VARS.items():
    if not os.getenv(var):
        missing_vars.append(f"{var}: {description}")

if missing_vars:
    error_msg = "Missing required environment variables:\n" + "\n".join(f"  - {var}" for var in missing_vars)
    logger.critical(error_msg)
    sys.exit(1)

logger.info("Environment validation successful")

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

app = FastAPI(
    title="Brax Fine Jewelers AI Assistant",
    version="2.0.0",
    description="Multi-tenant jewelry consultation chatbot with canonical LangChain implementation",
    docs_url="/admin/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/admin/redoc" if os.getenv("ENVIRONMENT") == "development" else None
)

# Security middleware
trusted_hosts = os.getenv("TRUSTED_HOSTS", "*.azurewebsites.net,localhost,127.0.0.1").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[host.strip() for host in trusted_hosts])

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS setup with secure defaults
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://*.braxjewelers.com,https://*.azurewebsites.net").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Session-ID"]
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={
        "url": str(request.url),
        "method": request.method,
        "client": request.client.host if request.client else "unknown"
    })
    return JSONResponse(
        status_code=500,
        content={
            "error": "An internal server error occurred",
            "request_id": str(uuid.uuid4())[:8]
        }
    )

# ─── LLM + CANONICAL MESSAGE HISTORY ─────────────────────────────────────────

# session_id -> InMemoryChatMessageHistory
_session_store: Dict[str, InMemoryChatMessageHistory] = {}

def _history_factory(config: Dict) -> InMemoryChatMessageHistory:
    """
    RunnableWithMessageHistory callback. Ensures a per-session
    InMemoryChatMessageHistory keyed by config['configurable']['session_id'].
    """
    cfg = (config or {}).get("configurable", {})
    session_id = cfg.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        cfg["session_id"] = session_id
        config["configurable"] = cfg

    if session_id not in _session_store:
        _session_store[session_id] = InMemoryChatMessageHistory()
    return _session_store[session_id]

# LLM configuration with environment variables
model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
temperature = float(os.getenv("TEMPERATURE", "0.9"))

llm = ChatOpenAI(model=model_name, max_tokens=max_tokens, temperature=temperature)

# Build canonical prompt: system + history + human
prompt_text = (
    " ".join(AGENT_ROLES["brax_jeweler"])
    if isinstance(AGENT_ROLES.get("brax_jeweler"), list)
    else AGENT_ROLES.get("brax_jeweler", "")
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", prompt_text),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)

# Base runnable and history wrapper
_base_chain = prompt | llm
chain = RunnableWithMessageHistory(
    _base_chain,
    _history_factory,
    input_messages_key="input",
    history_messages_key="history",
)

# ─── REQUEST MODEL ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_input: str = Field(..., max_length=1000, min_length=1)
    session_id: Optional[str] = None

    @field_validator('user_input')
    @classmethod
    def sanitize_input(cls, v):
        """Sanitize and validate user input"""
        v = v.strip()
        if not v:
            raise ValueError('Input cannot be empty')
        v = re.sub(r'<script.*?</script>', '', v, flags=re.DOTALL | re.IGNORECASE)
        v = re.sub(r'<.*?>', '', v)  # Remove HTML tags
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
        return v[:1000]

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

# ─── HEALTH CHECK ────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint for monitoring"""
    try:
        # Test LLM configuration
        llm_healthy = bool(os.getenv('OPENAI_API_KEY'))
        
        # Test template loading
        template_healthy = os.path.exists(TEMPLATE_DIR) and os.path.exists(os.path.join(TEMPLATE_DIR, "widget.html"))
        
        # Memory usage check
        session_count = len(_session_store)
        
        overall_status = "healthy" if all([llm_healthy, template_healthy]) else "degraded"
        
        return {
            "status": overall_status,
            "service": "Brax Fine Jewelers AI Assistant",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "llm_configured": llm_healthy,
                "templates_loaded": template_healthy,
                "active_sessions": session_count
            },
            "environment": {
                "python_version": sys.version.split()[0],
                "app_mode": os.getenv("ENVIRONMENT", "production")
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# ─── ROOT REDIRECT ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Redirect root URL to the widget"""
    return RedirectResponse(url="/widget")

# ─── CHAT ENDPOINT ───────────────────────────────────────────────────────────

def serialize_messages(messages: list[BaseMessage]):
    return [{"role": msg.type, "content": msg.content} for msg in messages]

@app.post("/chat")
@limiter.limit("20/minute")  # 20 requests per minute per IP
async def chat(request: Request, req: ChatRequest):
    try:
        session_id = req.session_id or str(uuid.uuid4())
        config = {"configurable": {"session_id": session_id}}

        # Invoke the LLM chain (history is auto-managed)
        res = chain.invoke({"input": req.user_input}, config=config)
        reply = res.content.strip()

        # Read back history for client visibility (optional)
        history_msgs = _session_store[session_id].messages

        logger.info(
            f"Chat processed for session: {session_id[:8]}...",
            extra={"session_id": session_id, "user_input_length": len(req.user_input)},
        )

        response = JSONResponse(
            {
                "reply": reply,
                "session_id": session_id,
                "history": serialize_messages(history_msgs),
            }
        )
        response.headers["X-Session-ID"] = session_id
        return response
    except ValueError as ve:
        logger.warning(f"Validation error in /chat: {ve}")
        return JSONResponse(status_code=400, content={"error": str(ve)})
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in /chat: {e}", exc_info=True)

        # Handle specific OpenAI API errors
        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            return JSONResponse(
                status_code=500,
                content={"error": "⚠️ API configuration issue. Please contact support or check your OpenAI API key."},
            )
        if "rate_limit" in error_msg.lower():
            return JSONResponse(
                status_code=429,
                content={"error": "⏱️ Too many requests. Please wait a moment and try again."},
            )
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred. Please try again later."},
        )

# ─── CLEAR CHAT ENDPOINT ──────────────────────────────────────────────────────

class ClearChatRequest(BaseModel):
    session_id: Optional[str] = None

@app.post("/clear_chat")
@limiter.limit("5/minute")  # 5 clear requests per minute per IP
async def clear_chat(request: Request, req: ClearChatRequest = None):
    """
    Clear chat history for a specific session or all sessions.
    """
    try:
        if req and req.session_id:
            if req.session_id in _session_store:
                _session_store[req.session_id].clear()
                logger.info(f"Cleared session: {req.session_id[:8]}...")
                return JSONResponse({"status": "ok", "message": "Session chat history cleared."})
            return JSONResponse(status_code=404, content={"error": "Session not found."})
        # Clear all sessions (admin)
        _session_store.clear()
        logger.info("Cleared all user sessions")
        return JSONResponse({"status": "ok", "message": "All chat history cleared."})
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
                    "image_url": "/images/solitaire-ring.jpg",
                },
                {
                    "id": "BR002",
                    "name": "Vintage Art Deco Collection",
                    "price": "$1,800 - $8,500",
                    "description": "Inspired by 1920s glamour with intricate details",
                    "image_url": "/images/art-deco-collection.jpg",
                },
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
                    "description": f"Exquisite {query} pieces featuring certified diamonds and precious metals",
                }
            ],
            "total_count": 1,
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
    session_id = str(uuid.uuid4())
    cfg = {"configurable": {"session_id": session_id}}
    while True:
        try:
            text = input("You: ").strip()
            if text.lower() in ("exit", "quit"):
                sys.exit(0)
            res = chain.invoke({"input": text}, config=cfg)
            reply = res.content.strip()
            print("Elena:", reply)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print("Error:", e)
