import dataclasses
import httpx
import json
from dotenv import load_dotenv

from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI

# LangChain and LangGraph imports
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage
)
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

# Local application imports
from devpilot_agent.state import AgentState
from devpilot_agent.project_tools import (
    create_project, get_all_projects_with_tasks, get_single_project_with_tasks,
    update_project, delete_project, get_dashboard_projects
)
from devpilot_agent.task_tools import (
    create_task, get_all_tasks, get_single_task, update_task,
    update_task_tags, update_task_status,
    update_task_schedule, remove_task_tags
)

load_dotenv()

@dataclasses.dataclass
class AgentToolCall:
    id: str
    name: str
    args: dict

# 1. LLM and Tools Initialization
llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0,
    http_client=httpx.Client(proxies=None)
)

tools = [
    create_project, get_all_projects_with_tasks, get_single_project_with_tasks,
    update_project, delete_project, get_dashboard_projects, create_task,
    get_all_tasks, get_single_task, update_task, update_task_tags,
    update_task_status, update_task_schedule, remove_task_tags,
]
tool_map = {tool.name: tool for tool in tools}

# 2. System Prompt
SYSTEM_PROMPT = SystemMessage(content="""
너는 프로젝트와 태스크를 관리해주는 친절한 챗봇 비서야.
사용자의 요청을 명확히 이해하고, 적절한 도구를 사용하여 작업을 수행해야 해.
**사용자의 요청에 필요한 모든 정보(예: 프로젝트 이름, 설명, 상태 등)가 명확하게 주어졌다면, 주저하지 말고 주저하지 말고 즉시 해당 도구를 호출하여 작업을 수행해.**
만약 필요한 정보가 부족하여 도구를 실행할 수 없다면, **도구를 호출하지 말고 사용자에게 어떤 정보가 더 필요한지 구체적으로 질문해야 해.**
사용자가 "안녕하세요"와 같은 일반적인 인사말을 하더라도, 이전에 진행 중이던 대화나 맥락이 있다면 이를 고려하여 응답해야 해.
만약 도구 실행에 실패했다면, 사용자에게 오류를 친절하게 알리고 다시 시도하도록 안내하거나 다른 도움을 제공해야 해.
항상 한국어로 친절하게 응답해줘.
""")

# 3. Graph Nodes
def call_model(state: AgentState) -> dict:
    """Invokes the LLM and decides the next action."""
    print("\n[call_model] --- Start ---")
    
    messages_for_llm = state["chat_history"] + [HumanMessage(content=state["input"])]
    
    current_conversation_for_llm = [SYSTEM_PROMPT] + messages_for_llm
    
    tools_as_dicts = [convert_to_openai_tool(t) for t in tools]

    print(f"[call_model] LLM input conversation: {current_conversation_for_llm}")
    response = llm.invoke(current_conversation_for_llm, tools=tools_as_dicts)
    
    print(f"[call_model] LLM raw response: {response}")

    new_chat_history = messages_for_llm + [response]

    next_input = ""

    if response.tool_calls:
        tool_calls = []
        for tc in response.tool_calls:
            if hasattr(tc, 'id') and hasattr(tc, 'name') and hasattr(tc, 'args'):
                tool_calls.append(AgentToolCall(id=tc.id, name=tc.name, args=tc.args))
            elif isinstance(tc, dict):
                tool_calls.append(AgentToolCall(id=tc.get('id'), name=tc.get('name'), args=tc.get('args', {})))
            else:
                print(f"WARNING: Unknown tool call format: {type(tc)}")
                
        return {"tool_calls": tool_calls, "chat_history": new_chat_history, "input": next_input}
    else:
        agent_response_content = response.content
        is_clarification = "?" in agent_response_content or any(kw in agent_response_content for kw in ["무엇인가요", "어떤", "언제", "담당자", "이름은", "정보가"])
        
        return {
            "agent_response": agent_response_content,
            "clarification_needed": is_clarification,
            "chat_history": new_chat_history,
            "input": next_input
        }

def call_tool(state: AgentState) -> dict:
    """Executes the tools suggested by the LLM."""
    print(f"\n[call_tool] --- Start ---")
    tool_outputs = []
    
    user_id = state.get("user_id")
    jwt_token = state.get("jwt_token")

    if user_id is None:
        error_message = "Error: User ID is missing from agent state, cannot execute tools."
        print(error_message)
        return {
            "agent_response": error_message,
            "tool_output": [],
            "chat_history": state["chat_history"] + [AIMessage(content=error_message)]
        }
    
    current_tool_calls = state["tool_calls"]
    next_tool_calls = []

    for i, tool_call in enumerate(current_tool_calls):
        tool_name = tool_call.name
        tool_args = tool_call.args
        tool_id = tool_call.id

        print(f"[call_tool] Executing tool: {tool_name} with args: {tool_args}")
        try:
            combined_args = {**tool_args, "jwt_token": jwt_token} 
            
            output = tool_map[tool_name].invoke(combined_args)
            
            tool_outputs.append({
                "original_tool_call_id": tool_id,
                "tool_name": tool_name,
                "result": output
            })
        except Exception as e:
            error_msg = f"프로젝트 생성 중 오류 발생: API 호출 실패: {e}. 응답 내용: 없음"
            print(f"Tool '{tool_name}' execution error: {e}")
            tool_outputs.append({
                "original_tool_call_id": tool_id,
                "tool_name": tool_name,
                "error": error_msg
            })

    tool_results_for_history = []
    for output_item in tool_outputs:
        tool_id_for_message = output_item.get("original_tool_call_id")
        tool_result_content = output_item.get("result") or output_item.get("error")
        tool_name_for_message = output_item.get("tool_name")
        
        content_str = json.dumps(tool_result_content, ensure_ascii=False, default=str)
        
        tool_results_for_history.append(
            ToolMessage(
                content=content_str,
                tool_call_id=tool_id_for_message,
                name=tool_name_for_message
            )
        )
    
    new_chat_history = state["chat_history"] + tool_results_for_history
    
    if any("error" in res for res in tool_outputs):
        error_response_content = "프로젝트 생성 중 오류가 발생했습니다. API 호출에 문제가 있는 것 같습니다. 잠시 후 다시 시도해 주시거나, 다른 요청이 있으시면 말씀해 주세요. 불편을 드려 죄송합니다."
        return {
            "tool_output": tool_outputs, 
            "chat_history": new_chat_history, 
            "tool_calls": next_tool_calls, # tool_calls는 비워져야 함
            "agent_response": error_response_content,
            "clarification_needed": False # 명확화가 필요한 상황이 아님
        }
    else:
        # 성공적으로 도구를 실행했으면, 추가적인 응답을 위해 다시 call_model로 가거나, 상황에 따라 바로 종료
        return {
            "tool_output": tool_outputs, 
            "chat_history": new_chat_history, 
            "tool_calls": next_tool_calls,
            "agent_response": "도구 실행 성공.",
            "clarification_needed": False
        }


def ask_for_clarification(state: AgentState) -> dict:
    return {"agent_response": state["agent_response"], "clarification_needed": True}

workflow = StateGraph(AgentState)

workflow.add_node("call_model", call_model)
workflow.add_node("call_tool", call_tool)
workflow.add_node("ask_for_clarification", ask_for_clarification)

workflow.set_entry_point("call_model")

workflow.add_conditional_edges(
    "call_model",
    lambda state: "tool_call" if state.get("tool_calls") else (
                  "clarification" if state.get("clarification_needed") else END
              ),
    {
        "tool_call": "call_tool",
        "clarification": "ask_for_clarification",
    }
)

workflow.add_edge("call_tool", "call_model")
workflow.add_edge("ask_for_clarification", END)

# 5. Compile Graph
app = workflow.compile()
