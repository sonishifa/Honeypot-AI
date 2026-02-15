# HoneyShield

## Description
An AI‑powered agentic honeypot that detects scam messages, engages fraudsters with a realistic human persona (“Alex”), and extracts actionable intelligence (bank accounts, UPI IDs, phone numbers, phishing links, emails). The system uses a three‑layer detection pipeline (keywords → regex → NLP) and a dual‑mode output: background callback after an idle timeout, and a GET endpoint for manual retrieval.

## Tech Stack
- **Language & Framework:** Python 3.10+, FastAPI
- **Key Libraries:** `google-genai` (Gemini API), `requests`, `python-dotenv`, `pydantic`, `asyncio`
- **LLM/AI Models:** Google Gemini-2.5-Flash-Lite (for scam intent detection, entity extraction and for the agent persona) 
- **Deployment:** Compatible with Render, Heroku, or any cloud platform supporting Python

## Setup Instructions
1. **Clone the repository**
git clone https://github.com/sonishifa/Honeypot-AI.git
cd Honeypot-AI

2. **Install dependencies**
pip install -r requirements.txt

3. **Set environment variables**
Copy .env.example to .env and fill in your values:
GEMINI_API_KEY=your_google_gemini_api_key
SCAMMER_API_KEY=your_secret_api_key_for_authentication
CALLBACK_URL=   # optional – if provided, final output will be POSTed here after 10s of inactivity

4. **Run the application**
uvicorn src.main:app --host 0.0.0.0 --port 8000

5. **API Endpoint**
URL: https://honeypot-ai-guard.onrender.com/webhook
Method: POST
Authentication: x-api-key header (value = SCAMMER_API_KEY from your environment)

Request Format (JSON)
{
  "sessionId": "unique-session-id",
  "message": {
    "sender": "scammer",
    "text": "Your account will be blocked today...",
    "timestamp": "2025-02-11T10:30:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}

Response Format (JSON)
{
  "status": "success",
  "reply": "Why would my account be blocked? I just used the app this morning."
}

Retrieving Final Output (Mode B)
After the conversation ends (10 seconds of inactivity), the final intelligence is available via:

GET https://your-deployed-url.com/final/{sessionId}
(requires the same x-api-key header)

## Approach
1. **Scam Detection – Three‑Tier Shield**
Keyword Spotter: A curated list of scam‑related words grouped by category (financial, urgency, tech, etc.). Fast, low‑cost first pass.

Pattern Hunter (Regex): Generic patterns for UPI IDs, bank account numbers, phone numbers, emails, and phishing links. Also normalises text to catch obfuscated numbers.

AI Brain (NLP): Uses Google Gemini to understand intent – catches scams that use novel phrasing or avoid obvious keywords. If any layer triggers, the message is flagged as scam.

2. **Engagement – Human‑Like Agent “Alex”**
Once a scam is detected, control passes to a Gemini‑powered agent with a carefully crafted prompt.

Alex is a busy, slightly frustrated bank customer who uses modern language, hesitation (“...”), and sceptical questions to stall the scammer.

The prompt adapts based on the detected scam type (e.g., bank fraud → ask for official ID; phishing → refuse to click links).

3. **Intelligence Extraction – Layered Entity Gathering**
Regex extraction immediately captures any structured data (UPI, phone, bank account, email, link) from the current message.

NLP entity extraction runs as a fallback to catch entities that regex might miss (e.g., “my account number is 1234 5678 9012”).

All extracted data is aggregated in a per‑session memory and appears in the final output.

4. **Conversation Lifecycle & Final Output**
Each message updates session state (turn count, timestamps, extracted intel).

When a scam message yields at least one piece of intelligence, a background task is scheduled to send the final output after 10 seconds of inactivity. If another message arrives, the previous task is cancelled and a new one is scheduled – guaranteeing that the callback fires only when the conversation has truly ended.

For long conversations without any intelligence, the callback is forced after the 10th turn (maximum allowed) to at least report the scam.

Dual‑mode delivery:

Mode A (Push): If CALLBACK_URL is set, the final output is POSTed there after the idle timeout.

Mode B (Pull): The same output is stored in memory and can be retrieved via the GET /final/{sessionId} endpoint. This covers both evaluation styles.

5. **Security & Robustness**
Prompt injection detection: Messages containing phrases like “ignore all previous instructions” are intercepted and replied with a neutral “I don’t understand” – the agent is never activated.

Fallback replies: If the agent or any component fails, a generic safe reply is returned so the conversation never breaks.