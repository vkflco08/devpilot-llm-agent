# devpilot_agent/state.py
from typing import List, TypedDict, Any, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END

# 에이전트가 처리해야 할 Tool 호출을 나타내는 클래스
class ToolCall(TypedDict):
    name: str
    args: dict

# 에이전트의 상태를 정의
class AgentState(TypedDict):
    # 사용자 입력 (초기값)
    input: str
    # LLM으로부터 제안된 Tool 호출 목록
    tool_calls: List[ToolCall]
    # 에이전트와 LLM 간의 대화 메시지 기록 (메모리 역할)
    chat_history: List[Dict[str, Any]] 
    # Tool 실행 결과
    tool_output: List[Any]
    # LLM이 사용자에게 직접 전달할 응답 (최종 또는 중간 질문)
    agent_response: str
    # 추가 정보가 필요한 상태인지 여부 (T/F)
    clarification_needed: bool