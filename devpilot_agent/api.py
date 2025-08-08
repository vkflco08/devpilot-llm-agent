"""
@file LangGraph 에이전트를 REST API로 노출하는 FastAPI 애플리케이션입니다.
@description 사용자 메시지를 받아 LangGraph 에이전트를 실행하고, 그 응답을 JSON 형태로 반환합니다.
"""

from fastapi import FastAPI, HTTPException, Depends, Request # Request 임포트 추가
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
import uvicorn
import os
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy.orm import Session
from devpilot_agent.database import get_db, create_db_tables, ChatMessage

# LangGraph 애플리케이션 및 상태 정의 임포트
from devpilot_agent.main import app as langgraph_app
from devpilot_agent.state import AgentState
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage
)
from langchain_core.messages import BaseMessage
from fastapi.middleware.cors import CORSMiddleware
import json

load_dotenv()

allowed_origins_str = os.getenv("DEVPILOT_FRONT_URL", "")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',') if origin.strip()]

allowed_origins_2_str = os.getenv("DEVPILOT_FRONT_URL_2", "")
allowed_origins.extend([origin.strip() for origin in allowed_origins_2_str.split(',') if origin.strip()])

if not allowed_origins:
    print("WARNING: DEVPILOT_FRONT_URL is not set or empty. CORS might be too restrictive or too open.")

api_app = FastAPI(
    title="DevPilot LLM Agent API",
    description="LangGraph 기반의 프로젝트/태스크 관리 챗봇 에이전트",
    version="0.1.0",
)

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api_app.on_event("startup")
async def startup_event():
    create_db_tables()

class ToolCallData(BaseModel):
    id: str
    name: str
    args: Dict[str, Any]

class ChatHistoryMessage(BaseModel):
    content: str
    type: Literal["human", "ai", "system", "tool", "user", "bot"] 
    tool_calls: Optional[List[ToolCallData]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ChatRequest(BaseModel):
    user_input: str = Field(..., description="사용자의 현재 메시지")
    chat_history: List[ChatHistoryMessage] = Field(default_factory=list, description="이전 대화 이력 (LangChain 메시지 형식)")
    user_id: Optional[int] = Field(None, description="현재 대화 중인 사용자의 ID")

class ChatResponse(BaseModel):
    response: str

class StoredChatMessageResponse(BaseModel):
    sender: str
    content: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    messages: List[StoredChatMessageResponse]

def convert_lc_message_to_chm(lc_message: BaseMessage) -> ChatHistoryMessage:
    if isinstance(lc_message, HumanMessage):
        return ChatHistoryMessage(content=lc_message.content, type="human")
    elif isinstance(lc_message, AIMessage):
        tool_calls_data = None
        if lc_message.tool_calls:
            tool_calls_data = []
            for tc in lc_message.tool_calls:
                if hasattr(tc, 'id') and hasattr(tc, 'name') and hasattr(tc, 'args'):
                    tool_calls_data.append(ToolCallData(id=tc.id, name=tc.name, args=tc.args))
                elif isinstance(tc, dict):
                    tool_calls_data.append(ToolCallData(id=tc.get('id'), name=tc.get('name'), args=tc.get('args', {})))
                else:
                    print(f"WARNING (api.py): Unrecognized tool call format in AIMessage: {type(tc)} - {tc}")
                    # Fallback to a generic representation if format is unknown
                    tool_calls_data.append(ToolCallData(id="unknown", name="unknown", args={"raw_data": str(tc)}))
        return ChatHistoryMessage(content=lc_message.content, type="ai", tool_calls=tool_calls_data)
    elif isinstance(lc_message, SystemMessage):
        return ChatHistoryMessage(content=lc_message.content, type="system")
    elif isinstance(lc_message, ToolMessage):
        return ChatHistoryMessage(content=lc_message.content, type="tool", tool_call_id=lc_message.tool_call_id, name=lc_message.name)
    else:
        print(f"WARNING (api.py): Unknown LangChain message type: {type(lc_message)}. Returning as generic bot message.")
        return ChatHistoryMessage(content=str(lc_message), type="bot")

@api_app.get("/health", summary="API 상태 확인")
async def health_check():
    return {"status": "ok", "message": "DevPilot LLM Agent API is running."}

@api_app.get("/chat/history/{user_id}", response_model=ChatHistoryResponse, summary="특정 사용자의 채팅 히스토리 조회")
async def get_chat_history(user_id: int, db: Session = Depends(get_db)):
    messages_from_db = db.query(ChatMessage).filter(ChatMessage.user_id == user_id).order_by(ChatMessage.timestamp).all()
    
    response_messages = [
        StoredChatMessageResponse(
            sender=msg.sender,
            content=msg.content,
            timestamp=msg.timestamp
        ) for msg in messages_from_db
    ]
    return ChatHistoryResponse(messages=response_messages)

@api_app.post("/chat", response_model=ChatResponse, summary="챗봇과 대화")
async def chat_with_agent(request: ChatRequest, http_request: Request, db: Session = Depends(get_db)):
    if request.user_id is None:
        raise HTTPException(status_code=400, detail="user_id is required")

    jwt_token: Optional[str] = None
    auth_header = http_request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]

    if jwt_token is None:
        error_msg = "JWT token is required for this operation."
        print(f"ERROR (api.py): {error_msg}")
        raise HTTPException(status_code=401, detail=error_msg)

    # 1. 사용자 메시지 데이터베이스에 저장
    user_msg_db = ChatMessage(
        user_id = request.user_id,
        sender = 'user',
        content = request.user_input,
    )
    db.add(user_msg_db)
    db.commit()
    db.refresh(user_msg_db)
    
    # 2. LangChain의 BaseMessage 객체로 chat_history 변환
    langchain_chat_history = []
    for raw_msg_data in request.chat_history:
        try:
            msg_data = ChatHistoryMessage.parse_obj(raw_msg_data)
        except Exception as e:
            print(f"WARNING: Failed to parse chat history message: {raw_msg_data}. Error: {e}")
            continue
        
        if msg_data.type == "user":
            langchain_chat_history.append(HumanMessage(content=msg_data.content))
        elif msg_data.type == "bot":
            langchain_chat_history.append(AIMessage(content=msg_data.content))
        elif msg_data.type == "human":
            langchain_chat_history.append(HumanMessage(content=msg_data.content))
        elif msg_data.type == "ai":
            if msg_data.tool_calls:
                langchain_tool_calls = []
                for tc in msg_data.tool_calls:
                    if isinstance(tc, dict):
                        langchain_tool_calls.append(ToolCall(id=tc.get('id'), name=tc.get('name'), args=tc.get('args', {})))
                    else:
                        langchain_tool_calls.append(ToolCall(id=tc.id, name=tc.name, args=tc.args))
                langchain_chat_history.append(AIMessage(content=msg_data.content, tool_calls=langchain_tool_calls))
            else:
                langchain_chat_history.append(AIMessage(content=msg_data.content))
        elif msg_data.type == "tool":
            if msg_data.tool_call_id and msg_data.name:
                langchain_chat_history.append(ToolMessage(content=msg_data.content, tool_call_id=msg_data.tool_call_id, name=msg_data.name))
            else:
                print(f"WARNING: Skipping malformed tool message in history: {msg_data}. Missing tool_call_id or name.")
        elif msg_data.type == "system":
            langchain_chat_history.append(SystemMessage(content=msg_data.content))
        else:
            print(f"WARNING: Skipping unknown message type in history: {msg_data}")
    
    # LangGraph 앱의 초기 상태 구성
    initial_state: AgentState = {
        "input": request.user_input,
        "chat_history": langchain_chat_history,
        "tool_calls": [],
        "tool_output": [],
        "agent_response": "",
        "clarification_needed": False,
        "user_id": request.user_id,
        "jwt_token": jwt_token
    }

    try:
        final_state = langgraph_app.invoke(initial_state)

        response_content = final_state.get("agent_response")
        
        if not response_content:
            if final_state.get("tool_output"):
                response_content = f"도구 실행 완료: {json.dumps(final_state['tool_output'], ensure_ascii=False, default=str)}"
            else:
                response_content = "챗봇이 응답을 생성하지 못했습니다."
        
        # 4. 에이전트 응답 데이터베이스에 저장
        agent_msg_db = ChatMessage(
            user_id = request.user_id,
            sender='bot',
            content=response_content,
        )
        db.add(agent_msg_db)
        db.commit()
        db.refresh(agent_msg_db)
        
        return ChatResponse(response=response_content)

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = f"챗봇 에이전트 실행 중 오류 발생: {str(e)}"
        print(f"ERROR (api.py): {error_msg}")
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

if __name__ == "__main__":
    uvicorn.run(api_app, host="0.0.0.0", port=8000)
