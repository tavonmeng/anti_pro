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

from typing import Dict

# Use a simple dictionary to hold sessions
sessions: Dict[str, AgentSession] = {}


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


def _parse_ai_response(response_text: str) -> dict:
    """解析 AI 回复，检测是否包含 JSON 数据块。"""
    match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            clean_text = response_text.replace(match.group(0), "").strip()
            return {
                "reply": clean_text,
                "requirements_gathered": True,
                "data": data
            }
        except json.JSONDecodeError:
            pass

    return {
        "reply": response_text,
        "requirements_gathered": False,
        "data": None
    }


@app.get("/start")
async def start_session(session_id: str):
    """
    初始化会话并返回 AI 的开场欢迎语。
    前端在用户打开对话框时调用此接口，展示开场白。
    """
    if session_id not in sessions:
        sessions[session_id] = AgentSession()

    greeting = sessions[session_id].get_greeting()
    return {
        "reply": greeting,
        "requirements_gathered": False,
        "data": None
    }


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    接收用户消息并返回 AI 回复。
    AI 会从用户第一条消息中自动提取信息，并针对缺失项逐一追问。
    """
    if req.session_id not in sessions:
        sessions[req.session_id] = AgentSession()

    agent = sessions[req.session_id]
    response_text = agent.chat(req.message)

    return _parse_ai_response(response_text)


@app.post("/submit_requirements")
async def submit_requirements(req: SubmitRequest):
    """接收并保存最终确认的需求数据。"""
    print("Received final requirements:", req.model_dump())
    return {"status": "success", "message": "Requirements saved successfully"}


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清除指定会话（用户重新开始时调用）。"""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "success", "message": f"Session {session_id} cleared"}
    return {"status": "not_found", "message": f"Session {session_id} not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
