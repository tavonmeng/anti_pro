import re
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import AgentSession

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use a simple dictionary to hold sessions for simplicity
sessions = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

class SubmitRequest(BaseModel):
    brand: str = ""
    background: str = ""
    target_group: str = ""
    brand_tone: str = ""
    content: str = ""
    style: str = ""
    prohibited_content: str = ""
    city: str = ""
    media_size: str = ""
    time_number: str = ""
    technology: str = ""
    budget: str = ""
    online_time: str = ""
    sales_contact: str = ""

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    if req.session_id not in sessions:
        sessions[req.session_id] = AgentSession()
    
    agent = sessions[req.session_id]
    response_text = agent.chat(req.message)
    
    # Check if AI returned a JSON block
    match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            # Strip the JSON from the user message, or keep it.
            clean_text = response_text.replace(match.group(0), "").strip()
            return {"reply": clean_text, "requirements_gathered": True, "data": data}
        except json.JSONDecodeError:
            pass
            
    return {"reply": response_text, "requirements_gathered": False, "data": None}

@app.post("/submit_requirements")
async def submit_requirements(req: SubmitRequest):
    # Here you would typically save to a database.
    print("Received final requirements:", req.model_dump())
    return {"status": "success", "message": "Requirements saved successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
