# devpilot_agent/main.py
import os
from dotenv import load_dotenv
from typing import List, Union, Callable
from langchain_openai import ChatOpenAI # 또는 langchain_anthropic 등
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor

from devpilot_agent.state import AgentState, ToolCall
from devpilot_agent.project_tools import (
    create_project,
    get_all_projects_with_tasks,
    get_single_project_with_tasks,
    update_project,
    delete_project,
    get_dashboard_projects
)
from devpilot_agent.task_tools import (
    create_task,
    get_all_tasks,
    get_single_task,
    update_task,
    update_task_tags,
    update_task_time,
    update_task_status,
    update_task_schedule,
    remove_task_tags,
)

load_dotenv()

# 1. LLM 모델 초기화
llm = ChatOpenAI(model="gpt-4o", temperature=0) # 사용할 LLM 모델 지정

# 2. Tool Executor 초기화
# LangChain의 @tool 데코레이터로 정의된 모든 Tool들을 리스트로 전달
tools = [
    create_project,
    get_all_projects_with_tasks,
    get_single_project_with_tasks,
    update_project,
    delete_project,
    get_dashboard_projects,
    create_task,
    get_all_tasks,
    get_single_task,
    update_task,
    update_task_tags,
    update_task_time,
    update_task_status,
    update_task_schedule,
    remove_task_tags,
] 
tool_executor = ToolExecutor(tools)

# 2. 시스템 프롬프트 정의
system_prompt = SystemMessage(content="""
    너는 프로젝트와 태스크를 관리해주는 친절한 챗봇 비서야.
사용자의 요청을 명확히 이해하고, 적절한 도구를 사용하여 작업을 수행해야 해.
만약 사용자의 요청이 모호하거나 필요한 정보가 부족하다면, **절대 도구를 호출하지 말고 사용자에게 필요한 정보를 구체적으로 질문해야 해.**
예시: "새 프로젝트를 만들어줘" -> "새 프로젝트의 이름은 무엇인가요?"
예시: "이 태스크 상태를 바꿔줘" -> "어떤 태스크의 상태를 무엇으로 변경할까요?"
항상 한국어로 친절하게 응답해줘.
    """)

# 3. Graph 노드 정의
def call_model(state: AgentState) -> dict:
    """
    LLM을 호출하여 사용자의 의도를 파악하고, Tool 호출을 제안하거나 최종 응답을 생성합니다.
    """
    messages = state["chat_history"]
    user_input = state["input"]
    
    # LLM 호출 시 시스템 프롬프트와 현재 대화 메시지를 함께 전달
    current_conversation = [system_prompt] + messages + [HumanMessage(content=user_input)]
    
    # LLM이 Tool을 사용할 수 있도록 tools 정보와 함께 호출
    response = llm.invoke(current_conversation, tools=tools)

    tool_calls = []
    if response.tool_calls: # LLM이 Tool 호출을 제안한 경우
        for tc in response.tool_calls:
            tool_calls.append(ToolCall(name=tc.name, args=tc.args))
        return {"tool_calls": tool_calls, "chat_history": state["chat_history"] + [HumanMessage(content=user_input), response]}
    else: 
        # LLM이 Tool을 호출하지 않고 응답을 생성한 경우
        # 최종 응답 또는 추가 질문
        is_clarification = "?" in agent_response_content or \
                           "무엇인가요" in agent_response_content or \
                           "어떤" in agent_response_content or \
                           "언제" in agent_response_content or \
                           "담당자" in agent_response_content or \
                           "이름은" in agent_response_content

        return {
            "agent_response": agent_response_content,
            "clarification_needed": is_clarification, # LLM이 질문을 던졌는지 여부
            "chat_history": state["chat_history"] + [HumanMessage(content=user_input), response]
        }

def call_tool(state: AgentState) -> dict:
    """
    LLM이 제안한 Tool 호출을 실제로 실행합니다.
    """
    tool_calls_to_execute = state["tool_calls"]
    tool_outputs = []
    # 사용자에게 보여줄 메시지
    tool_execution_messages = []
    for tool_call in tool_calls_to_execute:
        print(f"Executing tool: {tool_call['name']} with args: {tool_call['args']}")
        try:
            # ToolExecutor를 통해 Tool 실행
            output = tool_executor.invoke(tool_call)
            tool_outputs.append(output)
            tool_execution_messages.append(f"도구 '{tool_call['name']}' 실행 성공. 결과: {output}")
       
        except Exception as e:
            tool_outputs.append(f"Error executing tool {tool_call['name']}: {e}")
            tool_execution_messages.append(f"도구 '{tool_call['name']}' 실행 실패. 에러: {e}")

    tool_result_message = AIMessage(content="도구 실행 결과:\n" + "\n".join(str(output) for output in tool_outputs))

    # Tool 실행 결과를 다시 LLM에게 전달하여 다음 액션을 결정하거나 최종 응답 생성
    return {
        "tool_output": "\n".join(tool_outputs), 
        "chat_history": state["chat_history"] + [tool_result_message]
    }

def ask_for_clarification(state: AgentState) -> dict:
    """
    AgentState에 저장된 'agent_response'를 사용자에게 전달합니다.
    이 노드는 사용자의 추가 입력을 기다립니다
    """
    return {
        "agent_response": state["agent_response"],
        "clarification_needed": True
    }

# 4. Graph 정의 (StateGraph 사용)
workflow = StateGraph(AgentState)

workflow.add_node("call_model", call_model) # LLM 호출 노드
workflow.add_node("call_tool", call_tool)   # Tool 실행 노드
workflow.add_node("ask_for_clarification", ask_for_clarification) # 추가 질문 노드

# 그래프 시작점 설정
workflow.set_entry_point("call_model")

# 엣지 정의 (어떤 조건에서 다음 노드로 이동할지)
# call_model 노드 다음에는 tool_calls가 있으면 call_tool로, 없으면 END로 간다.
workflow.add_conditional_edges(
    "call_model",
    lambda state: "continue" if state.get("tool_calls") else "end" \
            ("clarification" if state.get("clarification_needed") else "final_response"), # tool_calls가 있으면 continue, 없으면 end
    {
        "continue": "call_tool",
        "clarification": "ask_for_clarification",
        "final_response": END
    }
)

# call_tool 노드 다음에는 다시 LLM을 호출하여 Tool 실행 결과를 바탕으로 응답을 생성하게 한다.
workflow.add_edge("call_tool", "call_model") 

# ask_for_clarification 노드 다음에는 다시 LLM을 호출하여 추가 질문을 처리한다.
workflow.add_edge("ask_for_clarification", "call_model") 

# 5. Graph 컴파일
app = workflow.compile()

# 6. 에이전트 실행 함수 (테스트용)
def run_agent(user_input: str, chat_history: List[BaseMessage] = []) -> str:
    initial_state = {
        "input": user_input, 
        "chat_history": chat_history, 
        "tool_calls": [], 
        "tool_output": "", 
        "final_response": "",
        "clarification_needed": False
    }

    # Graph를 실행하고 모든 중간 상태를 반환하도록 stream 대신 invoke 사용
    # 복잡한 대화 흐름에서는 stream을 사용하고 각 단계를 처리하는 것이 더 효과적일 수 있음.
    # 여기서는 최종 응답을 기다리는 방식으로 구현.
    for s in app.stream(initial_state):
        current_node_name = list(s.keys())[0] # 현재 실행 중인 노드 이름
        current_state = s[current_node_name] # 현재 노드의 결과 상태
        print(f"Node: {current_node_name}, State updates: {current_state}") # 디버깅용 로그

        if "__end__" in s:
            final_state = s["__end__"]
            break
    else: # for 루프가 break 없이 끝난 경우 (즉, 아직 END 노드에 도달하지 않은 경우)
        final_state = app.get_state(initial_state).values # 현재 상태를 가져옴 (LangGraph 0.0.187 이후)

    # 최종 응답 출력
    if final_state.get("agent_response"):
        return final_state["agent_response"]
    elif final_state.get("tool_output"): # Tool 실행 결과만 있고 LLM이 최종 응답을 만들지 못한 경우
         # 이 경우는 다시 LLM을 통해 사용자 친화적인 응답으로 변환해야 함
        return f"Tool executed, but no final response was generated. Raw output: {final_state['tool_output']}"
    else:
        return "응답을 생성할 수 없습니다. (현재 상태: 불분명)"


if __name__ == "__main__":
    print("LangGraph 에이전트 시작. '종료'라고 입력하면 종료합니다.")
    history: List[BaseMessage] = []
    while True:
        user_query = input("당신: ")
        if user_query.lower() == "종료":
            break

        response = run_agent(user_query, history)
        print(f"챗봇: {response}")

        # 대화 이력 업데이트 (간단한 예시)
        history.append(HumanMessage(content=user_query))
        history.append(AIMessage(content=response))
        # 실제 LangGraph에서는 chat_history가 자동으로 상태에 업데이트될 수 있도록 더 정교하게 구성
        # 여기서는 편의상 수동으로 추가합니다.
