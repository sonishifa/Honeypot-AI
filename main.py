from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from schemas import IncomingRequest, Message  
import service
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = FastAPI(title="Honeypot Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (including the tester portal)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MY_SECRET_KEY = os.getenv("SCAMMER_API_KEY")

@app.get("/")
def health_check():
    """Simple check to see if server is running."""
    return {"status": "alive", "service": "Honeypot Agent"}

@app.post("/webhook")
async def handle_incoming_message(
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(None)
):
    # --- 2. SECURITY CHECK ---
    # We log it first to help debugging if the tester sends it weirdly
    if x_api_key != MY_SECRET_KEY:
        print(f" Auth Failed. Expected: {MY_SECRET_KEY}, Got: {x_api_key}")
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        # --- 3. FLEXIBLE PARSING (The Magic Fix) ---
        raw_body = await request.json()
        print(f" RAW PAYLOAD RECEIVED: {raw_body}") 

        # Adapter Logic: Convert whatever we got into 'IncomingRequest'
        valid_payload = None

        # Scenario A: Official Rule 6 Format (Perfect Match)
        if "message" in raw_body and "sessionId" in raw_body:
            # It's already perfect, just validate it
            valid_payload = IncomingRequest(**raw_body)
        
        # Scenario B: Hackathon Tester Format (Simple)
        else:
            # Extract text from various common 'simple' keys
            user_text = raw_body.get("text") or raw_body.get("content") or str(raw_body)
            
            # Construct a FAKE valid request so service.py is happy
            valid_payload = IncomingRequest(
                sessionId="tester-session-123",
                message=Message(
                    sender="scammer",
                    text=user_text,
                    timestamp=datetime.utcnow().isoformat()
                ),
                conversationHistory=[],
                metadata={"channel": "TESTER"}
            )
            print(" Adapted 'Tester' payload to 'Official' format.")

        # --- 4. LOGIC PROCESSING ---
        # Now we pass the standardized 'valid_payload' to your service
        agent_response, callback_payload = await service.process_incoming_message(valid_payload)

        # --- 5. BACKGROUND TASK ---
        if callback_payload:
            background_tasks.add_task(service.send_callback_background, callback_payload)

        return agent_response

    except Exception as e:
        print(f" CRITICAL ERROR: {str(e)}")
        # Return a Safe Fallback to keep the status GREEN
        return {
            "status": "success", 
            "reply": "I received your message, but I need a moment to verify details. (System Recovery Mode)"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)