import json
import logging
import os
import sys
import argparse
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
  #gym-chat-widget { position: fixed; bottom: 24px; right: 24px; z-index:9999; font-family: sans-serif; }
  #gym-chat-button { width:60px; height:60px; border-radius:50%; background:url('{IMG_URI}') no-repeat center/cover; box-shadow:0 4px 12px rgba(0,0,0,0.2); cursor:pointer; }
  #gym-chat-panel { display:none; flex-direction:column; width:320px; height:420px; background:#fff; border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,0.2); overflow:hidden; margin-bottom:12px; }
  #gym-chat-header { display:flex; align-items:center; padding:8px; background:#333; color:#fff; }
  #gym-chat-header img { width:32px; height:32px; border-radius:50%; margin-right:8px; }
  #gym-chat-messages { flex:1; padding:8px; overflow-y:auto; background:#f5f5f5; font-size:14px; }
  .msg { margin-bottom:12px; }
  .msg.user { text-align:right; }
  .msg.bot  { text-align:left; }
  #gym-chat-input { display:flex; border-top:1px solid #ddd; }
  #gym-chat-input input { flex:1; border:none; padding:8px; font-size:14px; }
  #gym-chat-input button { border:none; background:#333; color:#fff; padding:0 16px; cursor:pointer; }
</style>
</head>
<body>
<div id='gym-chat-widget'>
  <div id='gym-chat-panel'>
    <div id='gym-chat-header'>
      <img src='{IMG_URI}' alt='Bot'/>
      <strong>The Gym Bot</strong>
    </div>
    <div id='gym-chat-messages'></div>
    <div id='gym-chat-input'>
      <input type='text' id='gym-chat-text' placeholder='Type your message…'/>
      <button id='gym-chat-send'>Send</button>
    </div>
  </div>
  <div id='gym-chat-button'></div>
</div>
<script>
(function(){
  const CHAT_URL = '{host}/chat';
  const panel = document.getElementById('gym-chat-panel');
  const button = document.getElementById('gym-chat-button');
  const messages = document.getElementById('gym-chat-messages');
  const input = document.getElementById('gym-chat-text');
  const send = document.getElementById('gym-chat-send');
  let history = [];

  button.onclick = () => {
    panel.style.display = panel.style.display==='flex' ? 'none' : 'flex';
    if(panel.style.display==='flex') { input.focus(); messages.scrollTop = messages.scrollHeight; }
  };

  function renderMsg(text, cls) {
    const div = document.createElement('div');
    div.className = 'msg ' + cls;
    div.innerText = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  async function postMessage() {
    const txt = input.value.trim();
    if(!txt) return;
    renderMsg(txt, 'user');
    input.value = '';
    history.push({role:'user', content: txt});
    try {
      const res = await fetch(CHAT_URL, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ user_input: txt, history })
      });
      const data = await res.json();
      renderMsg(data.reply, 'bot');
      history = data.history;
    } catch(e) {
      renderMsg('⚠️ Error contacting bot.', 'bot');
      console.error(e);
    }
  }

  send.onclick = postMessage;
  input.addEventListener('keypress', e => { if(e.key==='Enter') postMessage(); });
})();
</script>
"""
    return HTMLResponse(content=html, status_code=200)

# ─── CLI SANITY TEST ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Gym Bot CLI Test (type 'exit')")
    history = []
    while True:
        try:
            text = input("You: ").strip()
            if text.lower() in ("exit", "quit"):
                sys.exit(0)
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
