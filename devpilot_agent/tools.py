# devpilot_agent/tools.py
import requests
import os
from dotenv import load_dotenv
from langchain_core.tools import tool # LangChain의 tool 데코레이터 임포트

load_dotenv() # .env 파일 로드

SPRING_BACKEND_URL = os.getenv("SPRING_BACKEND_URL")

# 예시: 프로젝트 생성 Tool
@tool
def create_project(name: str, description: str = None) -> dict:
    """
    새로운 프로젝트를 생성합니다. 프로젝트 이름과 설명을 입력받습니다.
    :param name: 생성할 프로젝트의 이름 (필수)
    :param description: 프로젝트에 대한 간략한 설명 (선택 사항)
    :return: 생성된 프로젝트의 정보 (dict) 또는 에러 메시지
    """
    url = f"{SPRING_BACKEND_URL}/api/mcp/projects" # Spring MCP 엔드포인트 URL
    payload = {"name": name}
    if description:
        payload["description"] = description

    # 실제 Spring API 호출 로직
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # HTTP 에러 발생 시 예외 처리
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"프로젝트 생성 실패: {e}"}

# TODO: add_task, update_task_status, get_project_list 등 다른 Tool 함수들을 여기에 추가합니다.
# 각 Tool 함수는 @tool 데코레이터를 사용하고, 독스트링으로 설명을 제공해야 LLM이 이해하기 쉽습니다.