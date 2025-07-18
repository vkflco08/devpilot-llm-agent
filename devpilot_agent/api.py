
"""
@file LangGraph 에이전트를 REST API로 노출하는 FastAPI 애플리케이션입니다.
@description 사용자 메시지를 받아 LangGraph 에이전트를 실행하고, 그 응답을 JSON 형태로 반환합니다.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uvicorn
import os
from dotenv import load_dotenv

# LangGraph 애플리케이션 및 상태 정의 임포트
from devpilot_agent.main import app as langgraph_app # LangGraph 앱 임포트
from devpilot_agent.state import AgentState # AgentState 임포트

# .env 파일 로드 (환경 변수 사용을 위함)
load_dotenv()

# FastAPI 애플리케이션 초기화
api_app = FastAPI(
    title="DevPilot LLM Agent API",
    description="LangGraph 기반의 프로젝트/태스크 관리 챗봇 에이전트",
    version="0.1.0",
)

# --- 요청 및 응답 모델 정의 ---

# LangChain BaseMessage와 호환되는 메시지 모델 (채팅 이력용)
class ChatMessage(BaseModel):
    content: str
    type: str = Field(..., description="메시지 타입 (human, ai, system, tool)") # 'type' 대신 'role' 사용 권장 (OpenAI)

    # From LangChain BaseMessage
    # example: {"content": "Hello", "type": "human"}
    # example: {"content": "Hi there!", "type": "ai"}

# 챗봇 요청 모델
class ChatRequest(BaseModel):
    user_input: str = Field(..., description="사용자의 현재 메시지")
    chat_history: List[ChatMessage] = Field(default_factory=list, description="이전 대화 이력")
    # 추가적으로 사용자 ID 등을 받을 수 있음 (인증/권한 부여 시)
    user_id: Optional[int] = Field(None, description="현재 대화 중인 사용자의 ID")

# 챗봇 응답 모델
class ChatResponse(BaseModel):
    response: str = Field(..., description="챗봇의 응답 메시지")
    # 추가적으로 에이전트의 다음 행동, Tool 호출 정보 등을 반환할 수 있음
    # tool_calls: Optional[List[Dict[str, Any]]] = None # 디버깅용

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
    # LangChain의 BaseMessage 형태로 chat_history 재구성
    # LangChain의 BaseMessage는 `type` 대신 `role`을 사용합니다.
    # 'human' -> HumanMessage, 'ai' -> AIMessage
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage # 임포트 확인

    langchain_chat_history = []
    for msg in request.chat_history:
        if msg.type == "human":
            langchain_chat_history.append(HumanMessage(content=msg.content))
        elif msg.type == "ai":
            langchain_chat_history.append(AIMessage(content=msg.content))
        # 필요한 경우 'system' 메시지도 처리
        elif msg.type == "system":
            langchain_chat_history.append(SystemMessage(content=msg.content))
        # 다른 타입은 무시하거나 에러 처리

    # LangGraph 앱의 초기 상태 구성
    # user_id는 AgentState에 직접 없으므로, 필요하다면 AgentState에 추가하거나
    # LangGraph의 config에 넘겨서 Tool에서 접근할 수 있도록 해야 합니다.
    initial_state: AgentState = {
        "input": request.user_input,
        "chat_history": langchain_chat_history,
        "tool_calls": [],
        "tool_output": "",
        "agent_response": "",
        "clarification_needed": False,
        # "user_id": request.user_id # AgentState에 user_id 필드가 있다면 추가
    }

    try:
        # LangGraph 앱 실행
        # app.invoke는 최종 상태를 반환
        # app.stream을 사용하면 중간 단계를 스트리밍 받을 수 있음 (더 복잡)
        final_state = langgraph_app.invoke(initial_state)

        # 최종 응답 추출
        response_content = final_state.get("agent_response")
        
        if not response_content:
            # LLM이 최종 응답을 생성하지 않고 ToolOutput만 반환한 경우 (디버깅용)
            if final_state.get("tool_output"):
                response_content = f"도구 실행 완료. 원시 결과: {final_state['tool_output']}"
            else:
                response_content = "챗봇이 응답을 생성하지 못했습니다. 다시 시도해주세요."
        
        return ChatResponse(response=response_content)

    except Exception as e:
        # 에이전트 실행 중 오류 발생 시
        print(f"Error during agent execution: {e}")
        raise HTTPException(status_code=500, detail=f"챗봇 에이전트 실행 중 오류 발생: {e}")

# 개발 서버 실행 (Dockerfile에서 Uvicorn으로 실행될 것이므로, 이 부분은 로컬 개발/테스트용)
if __name__ == "__main__":
    # 이 api.py 파일을 직접 실행할 경우
    uvicorn.run(api_app, host="0.0.0.0", port=8000)
