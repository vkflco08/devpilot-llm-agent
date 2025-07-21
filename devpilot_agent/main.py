import os
import json
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any

from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI

# LangChain and LangGraph imports
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolCall, # 👈 Make sure this is imported
)
from langgraph.graph import StateGraph, END

# Local application imports
from devpilot_agent.state import AgentState, ToolCall as AgentToolCall # TypedDict for state
from devpilot_agent.project_tools import (
    create_project, get_all_projects_with_tasks, get_single_project_with_tasks,
    update_project, delete_project, get_dashboard_projects
)
from devpilot_agent.task_tools import (
    create_task, get_all_tasks, get_single_task, update_task,
    update_task_tags, update_task_time, update_task_status,
    update_task_schedule, remove_task_tags
)

load_dotenv()

# 1. LLM and Tools Initialization
llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0,
    #
    http_client=httpx.Client(proxies=None)
    )

tools = [
    create_project, get_all_projects_with_tasks, get_single_project_with_tasks,
    update_project, delete_project, get_dashboard_projects, create_task,
    get_all_tasks, get_single_task, update_task, update_task_tags,
    update_task_time, update_task_status, update_task_schedule, remove_task_tags,
]
tool_map = {tool.name: tool for tool in tools}

# 2. System Prompt
SYSTEM_PROMPT = SystemMessage(content="""
너는 프로젝트와 태스크를 관리해주는 친절한 챗봇 비서야.
사용자의 요청을 명확히 이해하고, 적절한 도구를 사용하여 작업을 수행해야 해.
만약 사용자의 요청이 모호하거나 필요한 정보가 부족하다면, **절대 도구를 호출하지 말고 사용자에게 필요한 정보를 구체적으로 질문해야 해.**
예시: "새 프로젝트를 만들어줘" -> "새 프로젝트의 이름은 무엇인가요?"
예시: "이 태스크 상태를 바꿔줘" -> "어떤 태스크의 상태를 무엇으로 변경할까요?"
항상 한국어로 친절하게 응답해줘.
""")

# --- Helper Functions for Data Conversion ---

def _convert_dict_to_langchain_message(msg_dict: Dict[str, Any]) -> BaseMessage:
    """Converts a dictionary from chat_history back to a LangChain message object."""
    msg_type = msg_dict.get("type")
    content = msg_dict.get("content", "")

    if msg_type == "human":
        return HumanMessage(content=content)
    elif msg_type == "ai":
        tool_calls_dicts = msg_dict.get("tool_calls")
        if tool_calls_dicts:
            # ✨ THIS IS THE CRITICAL FIX ✨
            # Convert dictionaries back to official ToolCall objects
            # before creating the AIMessage.
            parsed_tool_calls = [
                ToolCall(name=tc["name"], args=tc["args"], id=tc.get("id"))
                for tc in tool_calls_dicts
            ]
            return AIMessage(content=content, tool_calls=parsed_tool_calls)
        return AIMessage(content=content)
    # Return a default or handle other types if necessary
    return HumanMessage(content=content)

def _convert_aimessage_to_dict(message: AIMessage) -> Dict[str, Any]:
    """Converts an AIMessage object into a serializable dictionary for chat_history."""
    result = {"type": "ai", "content": message.content}
    if message.tool_calls:
        # Convert ToolCall objects into simple dictionaries
        result["tool_calls"] = [
            {"name": tc["name"], "args": tc["args"], "id": tc.get("id")}
            for tc in message.tool_calls
        ]
    return result

# 3. Graph Nodes

def call_model(state: AgentState) -> dict:
    """Invokes the LLM and decides the next action."""
    print("\n[call_model] --- Start ---")
    user_input = state["input"]
    
    # Convert history of dicts to list of message objects for the LLM
    langchain_chat_history = [_convert_dict_to_langchain_message(msg) for msg in state["chat_history"]]
    current_conversation = [SYSTEM_PROMPT] + langchain_chat_history + [HumanMessage(content=user_input)]
    
    # LangChain tool 객체를 OpenAI API가 요구하는 딕셔너리 형태로 변환합니다.
    tools_as_dicts = [convert_to_openai_tool(t) for t in tools]

    print(f"[call_model] LLM input conversation: {current_conversation}")
    # llm.invoke 호출 시 변환된 딕셔너리 리스트를 전달합니다.
    response = llm.invoke(current_conversation, tools=tools_as_dicts)
    
    print(f"[call_model] LLM raw response: {response}")

    # Convert new messages to dicts before adding to state
    human_msg_dict = {"type": "human", "content": user_input}
    ai_msg_dict = _convert_aimessage_to_dict(response)
    new_chat_history = state["chat_history"] + [human_msg_dict, ai_msg_dict]

    if response.tool_calls:
        tool_calls = [AgentToolCall(name=tc['name'], args=tc['args']) for tc in response.tool_calls]
        return {"tool_calls": tool_calls, "chat_history": new_chat_history}
    else:
        agent_response_content = response.content
        is_clarification = "?" in agent_response_content or any(kw in agent_response_content for kw in ["무엇인가요", "어떤", "언제", "담당자", "이름은"])
        return {
            "agent_response": agent_response_content,
            "clarification_needed": is_clarification,
            "chat_history": new_chat_history
        }

def call_tool(state: AgentState) -> dict:
    """Executes the tools suggested by the LLM."""
    print(f"\n[call_tool] --- Start ---")
    tool_outputs = []
    
    for tool_call in state["tool_calls"]:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        print(f"[call_tool] Executing tool: {tool_name} with args: {tool_args}")
        try:
            output = tool_map[tool_name](**tool_args)
            tool_outputs.append(output)
        except Exception as e:
            error_msg = f"Tool '{tool_name}' execution error: {e}"
            print(error_msg)
            tool_outputs.append({"error": error_msg})

    # Add tool results to chat history as simple dictionaries
    tool_results_for_history = []
    for output in tool_outputs:
        content_str = json.dumps(output, ensure_ascii=False, default=str)
        tool_results_for_history.append({
            "type": "tool",
            "content": f"Tool execution result: {content_str}",
        })
    
    new_chat_history = state["chat_history"] + tool_results_for_history
    return {"tool_output": tool_outputs, "chat_history": new_chat_history}

def ask_for_clarification(state: AgentState) -> dict:
    """Prepares the state for asking the user a clarifying question."""
    return {"agent_response": state["agent_response"], "clarification_needed": True}

# 4. Graph Definition
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
workflow.add_edge("ask_for_clarification", END) # End after asking a question to wait for user input

# 5. Compile Graph
app = workflow.compile()