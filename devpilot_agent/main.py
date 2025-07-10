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

# 3. Graph 노드 정의
def call_model(state: AgentState) -> dict:
    """
    LLM을 호출하여 사용자의 의도를 파악하고, Tool 호출을 제안하거나 최종 응답을 생성합니다.
    """
    messages = state["chat_history"]
    # LLM이 Tool을 사용할 수 있도록 tools 정보와 함께 호출
    response = llm.invoke(messages + [HumanMessage(content=state["input"])], tools=tools)

    tool_calls = []
    if response.tool_calls: # LLM이 Tool 호출을 제안한 경우
        for tc in response.tool_calls:
            tool_calls.append(ToolCall(name=tc.name, args=tc.args))
        return {"tool_calls": tool_calls, "chat_history": state["chat_history"] + [response]}
    else: # LLM이 바로 응답을 생성한 경우
        return {"final_response": response.content, "chat_history": state["chat_history"] + [response]}

def call_tool(state: AgentState) -> dict:
    """
    LLM이 제안한 Tool 호출을 실제로 실행합니다.
    """
    tool_calls_to_execute = state["tool_calls"]
    tool_outputs = []
    for tool_call in tool_calls_to_execute:
        print(f"Executing tool: {tool_call['name']} with args: {tool_call['args']}")
        try:
            # ToolExecutor를 통해 Tool 실행
            output = tool_executor.invoke(tool_call)
            tool_outputs.append(f"Tool {tool_call['name']} executed successfully: {output}")
        except Exception as e:
            tool_outputs.append(f"Error executing tool {tool_call['name']}: {e}")

    # Tool 실행 결과를 다시 LLM에게 전달하여 다음 액션을 결정하거나 최종 응답 생성
    return {"tool_output": "\n".join(tool_outputs), "chat_history": state["chat_history"] + [AIMessage(content="\n".join(tool_outputs))]}


# 4. Graph 정의 (StateGraph 사용)
workflow = StateGraph(AgentState)

workflow.add_node("call_model", call_model) # LLM 호출 노드
workflow.add_node("call_tool", call_tool)   # Tool 실행 노드

# 그래프 시작점 설정
workflow.set_entry_point("call_model")

# 엣지 정의 (어떤 조건에서 다음 노드로 이동할지)
# call_model 노드 다음에는 tool_calls가 있으면 call_tool로, 없으면 END로 간다.
workflow.add_conditional_edges(
    "call_model",
    lambda state: "continue" if state.get("tool_calls") else "end", # tool_calls가 있으면 continue, 없으면 end
    {
        "continue": "call_tool",
        "end": END # 최종 응답을 생성하고 종료
    }
)

# call_tool 노드 다음에는 다시 LLM을 호출하여 Tool 실행 결과를 바탕으로 응답을 생성하게 한다.
workflow.add_edge("call_tool", "call_model") 

# 5. Graph 컴파일
app = workflow.compile()

# 6. 에이전트 실행 함수 (테스트용)
def run_agent(user_input: str, chat_history: List[BaseMessage] = []) -> str:
    initial_state = {"input": user_input, "chat_history": chat_history, "tool_calls": [], "tool_output": "", "final_response": ""}

    # Graph를 실행하고 최종 상태를 반환
    final_state = app.invoke(initial_state) 

    # 최종 응답 출력
    if final_state.get("final_response"):
        return final_state["final_response"]
    elif final_state.get("tool_output"): # 만약 Tool 실행 후 LLM이 바로 응답을 생성하지 않고 Tool 결과만 있다면
         # 이 부분은 실제 서비스에서는 LLM이 Tool 결과를 보고 최종 응답을 생성하도록 다시 LLM을 거쳐야 합니다.
         # 여기서는 간단히 Tool 결과를 반환합니다.
        return f"Tool executed. Output: {final_state['tool_output']}"
    else:
        return "응답을 생성할 수 없습니다."


if __name__ == "__main__":
    print("LangGraph 에이전트 시작. '종료'라고 입력하면 종료합니다.")
    history = []
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
