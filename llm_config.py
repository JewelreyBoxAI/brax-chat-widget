# C:\AI_src\The-Gym Chatbot\llm_config.py

import os

# Pull in your OpenAI model settings from env or use these defaults
LLM_KWARGS = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", 0.9)),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", 1024)),
}

