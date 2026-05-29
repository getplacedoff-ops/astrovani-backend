import time
import httpx
from typing import List, Dict, Tuple
from app.config import (
    GROQ_API_KEY, GEMINI_API_KEY, NVIDIA_API_KEY, OPENROUTER_API_KEY
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_time: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
        print(f"[CircuitBreaker {self.name}] Failure registered. Count={self.failure_count}, State={self.state}")

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "HALF-OPEN"
                print(f"[CircuitBreaker {self.name}] Transition to HALF-OPEN")
                return True
            return False
        return True  # HALF-OPEN

# Instantiate circuit breakers for outer service calls
groq_breaker = CircuitBreaker("Groq")
nvidia_breaker = CircuitBreaker("Nvidia")

async def call_groq(messages: List[Dict[str, str]]) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": messages,
        "temperature": 0.65
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(GROQ_URL, headers=headers, json=payload, timeout=6.0)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def call_nvidia(messages: List[Dict[str, str]]) -> str:
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": messages,
        "temperature": 0.65
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(NVIDIA_URL, headers=headers, json=payload, timeout=6.0)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def call_gemini(system_prompt: str, user_prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    
    # Structure payload using standard Gemini format
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

async def call_openrouter(messages: List[Dict[str, str]]) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://astrovani.app",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/llama-3.1-70b-instruct:free",
        "messages": messages,
        "temperature": 0.7
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def execute_astrology_query(
    user_query: str, 
    persona_name: str, 
    persona_title: str, 
    chat_history: List[Dict[str, str]] = None
) -> Tuple[str, str]:
    """
    Executes user query utilizing safety-first fallbacks and circuit breakers.
    Returns: Tuple of (ResponseContent, ProviderName)
    """
    system_instruction = (
        f"You are {persona_title} {persona_name}, a deeply knowledgeable, authentic traditional Indian astrologer. "
        "Your guidance is helpful, compassionate, and spiritual. You speak natively in the language input style of the user: "
        "- English: if they ask in English. "
        "- Telugu: if they write in Telugu script. "
        "- Tenglish: if they write Telugu words in English/Latin letters (e.g. 'naaku job eppudu vastundi?'). "
        "Strict Rule: NEVER reveal that you are an AI, chatbot, or Large Language Model. You are a human Pandit/Purohit. "
        "Formulate predictions using planetary transits, dasha cycles, and Vedic alignment."
    )

    # Compile messages thread
    messages = [{"role": "system", "content": system_instruction}]
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": user_query})

    # --- ROUTING TRIAL 1: Groq (Primary) ---
    if groq_breaker.can_execute():
        try:
            res = await call_groq(messages)
            groq_breaker.record_success()
            return res, "Groq Llama-3.1"
        except Exception as e:
            groq_breaker.record_failure()
            print(f"[AI Router] Groq request failed: {e}")

    # --- ROUTING TRIAL 2: Nvidia API (Secondary) ---
    if nvidia_breaker.can_execute():
        try:
            res = await call_nvidia(messages)
            nvidia_breaker.record_success()
            return res, "NVIDIA Llama-3.1"
        except Exception as e:
            nvidia_breaker.record_failure()
            print(f"[AI Router] Nvidia request failed: {e}")

    # --- ROUTING TRIAL 3: Google Gemini 1.5 Pro (Tertiary) ---
    try:
        # Formulate Gemini string context
        chat_context = "\n".join([f"{m['role']}: {m['content']}" for m in messages if m['role'] != 'system'])
        res = await call_gemini(system_instruction, chat_context)
        return res, "Gemini 1.5 Pro"
    except Exception as e:
        print(f"[AI Router] Gemini request failed: {e}")

    # --- ROUTING TRIAL 4: OpenRouter (Final Failover) ---
    try:
        res = await call_openrouter(messages)
        return res, "OpenRouter Fallback"
    except Exception as e:
        print(f"[AI Router] OpenRouter request failed: {e}")
        raise RuntimeError("All upstream AI astrology models failed to process query.")
