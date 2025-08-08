import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import Optional, Literal, List, Dict, Any
from devpilot_agent.utils.api_caller import call_spring_api

load_dotenv()
SPRING_BACKEND_URL = os.getenv("SPRING_BACKEND_URL")

ProjectStatus = Literal["ACTIVE", "ARCHIVED", "COMPLETED"]

@tool
def create_project(
    project_name: str,
    project_description: Optional[str] = None,
    project_status: ProjectStatus = "ACTIVE",
    jwt_token: Optional[str] = None,
) -> dict:
    """
    새로운 프로젝트를 생성합니다. 프로젝트 이름, 설명, 상태를 입력받습니다.
    :param project_name: 생성할 프로젝트의 이름 (필수).
    :param project_description: 프로젝트에 대한 간략한 설명 (선택 사항).
    :param project_status: 프로젝트의 상태 ('ACTIVE', 'ARCHIVED', 'COMPLETED' 중 하나, 기본값은 'ACTIVE').
    :return: 생성된 프로젝트의 정보 (dict) 또는 에러 메시지.
    """
    payload = {
        "projectName": project_name,
        "projectDescription": project_description,
        "projectStatus": project_status
    }
    
    result = call_spring_api("POST", "/projects/new", payload=payload, jwt_token=jwt_token)
    if "error" in result:
        return {"error": f"프로젝트 생성 중 오류 발생: {result['error']}"}
    return {"message": "프로젝트가 성공적으로 생성되었습니다.", "project": result}


@tool
def get_all_projects_with_tasks(
    jwt_token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    현재 사용자의 모든 프로젝트와 그에 속한 태스크들을 조회합니다.
    :return: 프로젝트와 태스크 목록 (List[dict]) 또는 에러 메시지.
    """
    return call_spring_api("GET", "/projects/mypage", jwt_token=jwt_token)


@tool
def get_dashboard_projects(
    jwt_token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    현재 사용자의 진행 중인 프로젝트와 그에 속한 태스크들을 조회합니다.
    :return: 진행 중인 프로젝트 목록 (List[dict]) 또는 에러 메시지.
    """
    return call_spring_api("GET", "/projects/dashboard", jwt_token=jwt_token)


@tool
def get_single_project_with_tasks(
    project_id: int,
    jwt_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    특정 ID의 단일 프로젝트와 그에 속한 태스크들을 조회합니다.
    :param project_id: 조회할 프로젝트의 고유 ID (필수).
    :return: 단일 프로젝트 정보 (dict) 또는 에러 메시지.
    """
    return call_spring_api("GET", f"/projects/{project_id}", jwt_token=jwt_token)


@tool
def update_project(
    project_id: int,
    project_name: Optional[str] = None,
    project_description: Optional[str] = None,
    project_status: Optional[ProjectStatus] = None,
    jwt_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    기존 프로젝트의 정보를 수정합니다. 수정할 필드만 입력하면 됩니다.
    :param project_id: 수정할 프로젝트의 고유 ID (필수).
    :param project_name: 프로젝트의 새로운 이름 (선택 사항).
    :param project_description: 프로젝트의 새로운 설명 (선택 사항).
    :param project_status: 프로젝트의 새로운 상태 (선택 사항).
    :return: 수정된 프로젝트의 정보 (dict) 또는 에러 메시지.
    """
    payload = {}
    if project_name:
        payload["projectName"] = project_name
    if project_description:
        payload["projectDescription"] = project_description
    if project_status:
        payload["projectStatus"] = project_status
    
    if not payload:
        return {"error": "수정할 프로젝트 정보가 제공되지 않았습니다."}

    return call_spring_api("PUT", f"/projects/{project_id}", payload=payload, jwt_token=jwt_token)


@tool
def delete_project(
    project_id: int,
    jwt_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    특정 프로젝트를 삭제합니다. 프로젝트와 관련된 모든 태스크도 함께 삭제됩니다.
    :param project_id: 삭제할 프로젝트의 고유 ID (필수).
    :return: 성공 메시지 또는 에러 메시지.
    """
    return call_spring_api("DELETE", f"/projects/{project_id}", jwt_token=jwt_token)
