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

# GHL MCP Client
from .ghl_mcp_client import create_ghl_client, GHLMCPClient, ContactModel, OpportunityModel, MessageModel

# Tavily Search Client
from .tavily_client import create_tavily_client, TavilySearchClient, SearchResponse, format_search_results

# LangChain Tools
from .langchain_tools import create_langchain_tools

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

# ─── GHL MCP CLIENT INITIALIZATION ───────────────────────────────────────────

# Initialize GHL MCP client if enabled
ghl_client: Optional[GHLMCPClient] = None
if os.getenv("GHL_MCP_ENABLED", "false").lower() == "true":
    ghl_client = create_ghl_client()
    if ghl_client:
        logger.info("GHL MCP client initialized successfully")
    else:
        logger.warning("GHL MCP client initialization failed")
else:
    logger.info("GHL MCP integration disabled")

# Initialize Tavily Search client
tavily_client: Optional[TavilySearchClient] = create_tavily_client()
if tavily_client:
    logger.info("Tavily Search client initialized successfully")
else:
    logger.info("Tavily Search client not available - web search features disabled")

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

def _history_factory(session_id: str) -> InMemoryChatMessageHistory:
    """
    RunnableWithMessageHistory callback. Ensures a per-session
    InMemoryChatMessageHistory keyed by session_id.
    """
    if not session_id:
        session_id = str(uuid.uuid4())

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

# Create LangChain tools
langchain_tools = create_langchain_tools(tavily_client)

# Enhanced LLM with tools (if available)
if langchain_tools:
    llm_with_tools = llm.bind_tools(langchain_tools)
    logger.info(f"LangChain agent enhanced with {len(langchain_tools)} tools")
else:
    llm_with_tools = llm
    logger.info("LangChain agent running without additional tools")

# Base runnable and history wrapper
_base_chain = prompt | llm_with_tools
chain = RunnableWithMessageHistory(
    _base_chain,
    _history_factory,
    input_messages_key="input",
    history_messages_key="history",
    get_session_id=lambda config: config["configurable"]["session_id"]
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

class SearchRequest(BaseModel):
    query: str = Field(..., max_length=500, min_length=1)
    search_type: Optional[str] = Field("general", description="general, market, product, price, trends")
    max_results: Optional[int] = Field(5, ge=1, le=10)
    include_answer: Optional[bool] = True

# ─── HEALTH CHECK ────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint for monitoring"""
    try:
        # Test LLM configuration
        llm_healthy = bool(os.getenv('OPENAI_API_KEY'))
        
        # Test template loading
        template_healthy = os.path.exists(TEMPLATE_DIR) and os.path.exists(os.path.join(TEMPLATE_DIR, "widget.html"))
        
        # Test GHL MCP connection
        ghl_healthy = True
        ghl_status = "disabled"
        if ghl_client:
            try:
                test_response = ghl_client.test_connection()
                ghl_healthy = test_response.success
                ghl_status = "connected" if ghl_healthy else "connection_failed"
            except Exception:
                ghl_healthy = False
                ghl_status = "error"
        
        # Test Tavily Search connection
        tavily_healthy = True
        tavily_status = "disabled"
        if tavily_client:
            try:
                test_response = tavily_client.test_connection()
                tavily_healthy = test_response.success
                tavily_status = "connected" if tavily_healthy else "connection_failed"
            except Exception:
                tavily_healthy = False
                tavily_status = "error"
        
        # Memory usage check
        session_count = len(_session_store)
        
        overall_status = "healthy" if all([llm_healthy, template_healthy, ghl_healthy or not ghl_client, tavily_healthy or not tavily_client]) else "degraded"
        
        return {
            "status": overall_status,
            "service": "Brax Fine Jewelers AI Assistant",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "llm_configured": llm_healthy,
                "templates_loaded": template_healthy,
                "ghl_mcp_status": ghl_status,
                "tavily_search_status": tavily_status,
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

# ─── GHL CRM ENDPOINTS ──────────────────────────────────────────────────────

@app.post("/crm/create-contact")
async def create_crm_contact(contact: ContactModel):
    """Create a new contact in GoHighLevel CRM"""
    if not ghl_client:
        return JSONResponse(
            status_code=503,
            content={"error": "GHL CRM integration not available"}
        )
    
    try:
        response = ghl_client.create_contact(contact)
        if response.success:
            logger.info(f"Contact created successfully: {contact.email}")
            return JSONResponse({
                "success": True,
                "contact_id": response.data.get("id") if response.data else None,
                "message": "Contact created successfully"
            })
        else:
            return JSONResponse(
                status_code=400,
                content={"error": response.error}
            )
    except Exception as e:
        logger.error(f"Error creating CRM contact: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to create contact in CRM"}
        )

@app.post("/crm/schedule-appointment")
async def schedule_jewelry_consultation(request: AppointmentRequest):
    """Schedule appointment and create contact in GHL CRM"""
    if not ghl_client:
        # Fallback to direct appointment scheduling
        return await schedule_consultation_fallback(request)
    
    try:
        # First, create or update contact in CRM
        contact = ContactModel(
            firstName=request.customer_name.split(' ')[0] if ' ' in request.customer_name else request.customer_name,
            lastName=' '.join(request.customer_name.split(' ')[1:]) if ' ' in request.customer_name else "",
            email=request.email,
            phone=request.phone,
            tags=["Jewelry Consultation", "Website Lead", request.consultation_type.replace('_', ' ').title()]
        )
        
        contact_response = ghl_client.upsert_contact(contact, email=request.email)
        
        if not contact_response.success:
            logger.warning(f"Failed to create CRM contact: {contact_response.error}")
            return await schedule_consultation_fallback(request)
            
        contact_id = contact_response.data.get("id") if contact_response.data else None
        
        # Create opportunity for jewelry consultation
        if contact_id:
            opportunity = OpportunityModel(
                name=f"Jewelry Consultation - {request.customer_name}",
                contactId=contact_id,
                pipelineId="default",  # This should be configured based on your GHL setup
                stageId="new_lead",    # This should be configured based on your GHL setup
                monetaryValue=0.0,
                status="active"
            )
            
            # Note: You'll need to get the actual pipeline/stage IDs from GHL
            pipelines_response = ghl_client.get_pipelines()
            if pipelines_response.success and pipelines_response.data:
                # Use the first available pipeline for demo purposes
                pipelines = pipelines_response.data.get("pipelines", [])
                if pipelines:
                    opportunity.pipelineId = pipelines[0].get("id")
                    stages = pipelines[0].get("stages", [])
                    if stages:
                        opportunity.stageId = stages[0].get("id")
        
        # Send confirmation message if messaging is available
        if contact_id:
            try:
                message = MessageModel(
                    conversationId=contact_id,  # This might need adjustment based on GHL structure
                    message=f"Thank you for scheduling a {request.consultation_type.replace('_', ' ')} consultation at Brax Fine Jewelers. We'll contact you within 24 hours to confirm your appointment for {request.preferred_date}.",
                    type="SMS"
                )
                ghl_client.send_message(message)
            except Exception as msg_error:
                logger.warning(f"Failed to send confirmation message: {msg_error}")
        
        appointment_data = {
            "appointment_id": f"BRAX-{request.customer_name[:3].upper()}-{contact_id or '001'}",
            "customer": request.customer_name,
            "email": request.email,
            "phone": request.phone,
            "date": request.preferred_date,
            "type": request.consultation_type,
            "status": "pending_confirmation",
            "crm_contact_id": contact_id,
            "message": "Thank you for scheduling with Brax Fine Jewelers. We'll contact you within 24 hours to confirm your appointment."
        }
        
        return JSONResponse(appointment_data)
        
    except Exception as e:
        logger.error(f"Error in CRM appointment scheduling: {e}", exc_info=True)
        return await schedule_consultation_fallback(request)

async def schedule_consultation_fallback(request: AppointmentRequest):
    """Fallback appointment scheduling without CRM integration"""
    try:
        appointment_data = {
            "appointment_id": f"BRAX-{request.customer_name[:3].upper()}-FALLBACK",
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
        logger.error(f"Error in fallback appointment scheduling: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to schedule appointment. Please call (949) 250-9949."}
        )

@app.get("/crm/contacts")
async def get_crm_contacts(limit: int = 20, offset: int = 0, query: str = None):
    """Get contacts from GHL CRM"""
    if not ghl_client:
        return JSONResponse(
            status_code=503,
            content={"error": "GHL CRM integration not available"}
        )
    
    try:
        response = ghl_client.get_contacts(limit=limit, offset=offset, query=query)
        if response.success:
            return JSONResponse(response.data)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": response.error}
            )
    except Exception as e:
        logger.error(f"Error fetching CRM contacts: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to fetch contacts from CRM"}
        )

@app.get("/crm/opportunities")
async def get_crm_opportunities(contact_id: str = None, limit: int = 20, offset: int = 0):
    """Get opportunities from GHL CRM"""
    if not ghl_client:
        return JSONResponse(
            status_code=503,
            content={"error": "GHL CRM integration not available"}
        )
    
    try:
        response = ghl_client.search_opportunity(
            contact_id=contact_id, 
            limit=limit, 
            offset=offset
        )
        if response.success:
            return JSONResponse(response.data)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": response.error}
            )
    except Exception as e:
        logger.error(f"Error fetching CRM opportunities: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to fetch opportunities from CRM"}
        )

# ─── WEB SEARCH ENDPOINTS ────────────────────────────────────────────────────

@app.post("/search")
@limiter.limit("10/minute")  # 10 searches per minute per IP
async def web_search(request: Request, search_req: SearchRequest):
    """Perform web search using Tavily API for jewelry-related queries"""
    if not tavily_client:
        return JSONResponse(
            status_code=503,
            content={"error": "Web search service not available"}
        )
    
    try:
        # Route to specialized search methods based on search type
        if search_req.search_type == "market":
            response = tavily_client.jewelry_market_search(search_req.query)
        elif search_req.search_type == "product":
            response = tavily_client.product_research(search_req.query)
        elif search_req.search_type == "price":
            response = tavily_client.price_comparison(search_req.query)
        elif search_req.search_type == "trends":
            response = tavily_client.trend_analysis(search_req.query)
        else:
            # General search
            response = tavily_client.search(
                query=search_req.query,
                max_results=search_req.max_results,
                include_answer=search_req.include_answer
            )
        
        if response.success:
            logger.info(f"Web search successful: {search_req.query} ({search_req.search_type})")
            return JSONResponse({
                "success": True,
                "query": response.query,
                "answer": response.answer,
                "results": [
                    {
                        "title": result.title,
                        "url": result.url,
                        "content": result.content[:500],  # Limit content length
                        "score": result.score
                    }
                    for result in response.results
                ],
                "follow_up_questions": response.follow_up_questions,
                "search_time": response.search_time,
                "search_type": search_req.search_type
            })
        else:
            logger.warning(f"Web search failed: {response.error}")
            return JSONResponse(
                status_code=400,
                content={"error": response.error}
            )
    
    except Exception as e:
        logger.error(f"Error in web search: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to perform web search"}
        )

@app.get("/search/jewelry-trends")
async def get_jewelry_trends(category: str = "engagement rings"):
    """Get current jewelry trends for a specific category"""
    if not tavily_client:
        return JSONResponse(
            status_code=503,
            content={"error": "Web search service not available"}
        )
    
    try:
        response = tavily_client.trend_analysis(category)
        
        if response.success:
            return JSONResponse({
                "category": category,
                "trends_summary": response.answer,
                "key_trends": [result.title for result in response.results[:5]],
                "sources": [
                    {"title": result.title, "url": result.url}
                    for result in response.results[:3]
                ],
                "updated": datetime.utcnow().isoformat()
            })
        else:
            return JSONResponse(
                status_code=400,
                content={"error": response.error}
            )
    
    except Exception as e:
        logger.error(f"Error fetching jewelry trends: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to fetch jewelry trends"}
        )

@app.get("/search/market-info")
async def get_market_info(query: str):
    """Get jewelry market information and pricing insights"""
    if not tavily_client:
        return JSONResponse(
            status_code=503,
            content={"error": "Web search service not available"}
        )
    
    try:
        response = tavily_client.jewelry_market_search(query)
        
        if response.success:
            return JSONResponse({
                "query": query,
                "market_summary": response.answer,
                "insights": [
                    {
                        "source": result.title,
                        "insight": result.content[:300],
                        "url": result.url
                    }
                    for result in response.results[:4]
                ],
                "related_questions": response.follow_up_questions,
                "search_time": response.search_time
            })
        else:
            return JSONResponse(
                status_code=400,
                content={"error": response.error}
            )
    
    except Exception as e:
        logger.error(f"Error fetching market info: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to fetch market information"}
        )

# ─── LEGACY JEWELRY ENDPOINTS (Deprecated) ──────────────────────────────────

@app.post("/jewelry/recommend")
async def recommend_jewelry(request: JewelryRequest):
    """
    DEPRECATED: Legacy jewelry recommendation endpoint
    Use /crm/create-contact and /crm/schedule-appointment instead
    """
    logger.warning("Using deprecated /jewelry/recommend endpoint")
    try:
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
            ],
            "deprecated": True,
            "migration_note": "This endpoint is deprecated. Please use /crm/create-contact for lead capture."
        }
        return JSONResponse(recommendations)
    except Exception as e:
        logger.error(f"Error in legacy jewelry recommendations: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to process jewelry recommendation request."}
        )

@app.post("/appointment/schedule")
async def schedule_consultation(request: AppointmentRequest):
    """
    DEPRECATED: Use /crm/schedule-appointment instead
    """
    logger.warning("Using deprecated /appointment/schedule endpoint")
    return await schedule_consultation_fallback(request)

@app.get("/inventory/search")
async def search_inventory(query: str, budget_min: Optional[float] = None, budget_max: Optional[float] = None):
    """
    DEPRECATED: Legacy inventory search
    """
    logger.warning("Using deprecated /inventory/search endpoint")
    try:
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
            "deprecated": True,
            "migration_note": "This endpoint is deprecated. Contact information should be captured via /crm/create-contact."
        }
        return JSONResponse(search_results)
    except Exception as e:
        logger.error(f"Error in legacy inventory search: {e}", exc_info=True)
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
