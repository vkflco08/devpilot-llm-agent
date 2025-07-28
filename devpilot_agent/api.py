"""
@file LangGraph 에이전트를 REST API로 노출하는 FastAPI 애플리케이션입니다.
@description 사용자 메시지를 받아 LangGraph 에이전트를 실행하고, 그 응답을 JSON 형태로 반환합니다.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field # Field 임포트 확인
from typing import List, Dict, Any, Optional
import uvicorn
import os
from dotenv import load_dotenv

# LangGraph 애플리케이션 및 상태 정의 임포트
from devpilot_agent.main import app as langgraph_app # LangGraph 앱 임포트
from devpilot_agent.state import AgentState # AgentState 임포트
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage # 임포트 확인
from fastapi.middleware.cors import CORSMiddleware

# .env 파일 로드 (환경 변수 사용을 위함)
load_dotenv()

allowed_origins_str = os.getenv("DEVPILOT_FRONT_URL", "") # 기본값을 빈 문자열로 설정
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',') if origin.strip()]

# 만약 허용할 Origin이 없다면 (예: 환경 변수가 비어있는 경우)
# 개발 중이거나 모든 Origin을 허용해야 하는 경우를 대비해 "[]" 또는 ["*"]와 같은 기본값을 설정할 수 있습니다.
# 프로덕션에서는 반드시 구체적인 Origin을 지정해야 합니다.
if not allowed_origins:
    # 예: 허용된 Origin이 없으면 오류 발생 (보안 강화)
    print("WARNING: DEVPILOT_FRONT_URL is not set or empty. CORS might be too restrictive or too open.")

# FastAPI 애플리케이션 초기화
api_app = FastAPI(
    title="DevPilot LLM Agent API",
    description="LangGraph 기반의 프로젝트/태스크 관리 챗봇 에이전트",
    version="0.1.0",
)


api_app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, # 리스트 형태로 변환된 allowed_origins 사용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 요청 및 응답 모델 정의 ---

# ChatRequest 모델
class ChatRequest(BaseModel):
    user_input: str = Field(..., description="사용자의 현재 메시지")
    # chat_history를 List[Dict[str, str]]로 유지하여 FastAPI의 Pydantic 검증을 단순화
    chat_history: List[Dict[str, str]] = Field(default_factory=list, description="이전 대화 이력 (content, type 필드를 가진 딕셔너리 리스트)")
    user_id: Optional[int] = Field(None, description="현재 대화 중인 사용자의 ID")

# 챗봇 응답 모델
class ChatResponse(BaseModel):
    response: str = Field(..., description="챗봇의 응답 메시지")

# --- API 엔드포인트 정의 ---

@api_app.get("/health", summary="API 상태 확인")
async def health_check():
    """
    API 서버의 상태를 확인합니다.
    """
    return {"status": "ok", "message": "DevPilot LLM Agent API is running."}

@api_app.post("/chat", response_model=ChatResponse, summary="챗봇과 대화")
async def chat_with_agent(request: ChatRequest):
    """
    사용자의 메시지를 받아 LangGraph 에이전트를 실행하고 응답을 반환합니다.
    """
    # langchain_chat_history = []
    # request.chat_history는 Dict[str, str] 리스트로 들어옴
    # 이를 LangChain의 BaseMessage 객체로 변환하여 AgentState에 전달
    # for msg_dict in request.chat_history: 
    #     msg_content = msg_dict.get("content", "")
    #     msg_type = msg_dict.get("type", "")

    #     if msg_type == "human":
    #         langchain_chat_history.append(HumanMessage(content=msg_content)) # ✨ 실제 HumanMessage 객체로 변환
    #     elif msg_type == "ai":
    #         langchain_chat_history.append(AIMessage(content=msg_content)) # ✨ 실제 AIMessage 객체로 변환
    #     elif msg_type == "system":
    #         langchain_chat_history.append(SystemMessage(content=msg_content)) # ✨ 실제 SystemMessage 객체로 변환
        # 다른 타입은 무시하거나 에러 처리

    # LangGraph 앱의 초기 상태 구성
    # AgentState의 chat_history는 List[BaseMessage]를 기대하므로, 위에서 변환된 객체를 전달
    initial_state: AgentState = {
        "input": request.user_input,
        "chat_history": request.chat_history, # List[Dict[str, str]]
        "tool_calls": [],
        "tool_output": [],
        "agent_response": "",
        "clarification_needed": False,
        # "user_id": request.user_id # AgentState에 user_id 필드가 있다면 추가
    }

    try:
        # 동기 함수인 invoke를 사용합니다.
        final_state = langgraph_app.invoke(initial_state)

        response_content = final_state.get("agent_response")
        
        if not response_content:
            if final_state.get("tool_output"):
                response_content = f"도구 실행 완료: {json.dumps(final_state['tool_output'], ensure_ascii=False, default=str)}"
            else:
                response_content = "챗봇이 응답을 생성하지 못했습니다."
        
        return ChatResponse(response=response_content)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"챗봇 에이전트 실행 중 오류 발생: {str(e)}"
        )

# 개발 서버 실행 (Dockerfile에서 Uvicorn으로 실행될 것이므로, 이 부분은 로컬 개발/테스트용)
if __name__ == "__main__":
    uvicorn.run(api_app, host="0.0.0.0", port=8000)
