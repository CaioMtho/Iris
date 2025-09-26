from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from backend.services.conversation_service import handle_chat

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatIn(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str | None = None
    max_tokens: int | None = 512
    temperature: float | None = 0.0

@router.post("/")
async def chat_endpoint(payload: ChatIn):
    session_id = payload.session_id or str(uuid.uuid4())
    out = await handle_chat(payload.message, session_id=session_id, user_id=payload.user_id,
                            max_tokens=payload.max_tokens or 512, temperature=payload.temperature or 0.0)
    out["session_id"] = session_id
    return out
