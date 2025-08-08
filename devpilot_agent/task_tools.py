from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import Optional, Literal, List, Dict, Any
from devpilot_agent.utils.api_caller import call_spring_api

load_dotenv()

TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE", "BLOCKED"]

# --- 태스크 CRUD Tools ---

@tool
def create_task(
    title: str,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    priority: Optional[int] = None,
    due_date: Optional[str] = None,
    estimated_time_hours: Optional[float] = None,
    status: TaskStatus = "TODO",
    project_id: Optional[int] = None,
    jwt_token: Optional[str] = None,
) -> dict:
    """
    새로운 태스크를 생성합니다. 태스크의 제목, 설명, 태그, 우선순위, 마감일, 예상 소요 시간, 상태, 관련 프로젝트 ID를 입력받습니다.
    우선순위는 1(높음)부터 5(낮음)까지의 숫자입니다.

    :param title: 태스크의 제목 (필수).
    :param description: 태스크에 대한 간략한 설명 (선택 사항).
    :param tags: 태스크 관련 콤마로 구분된 태그들 (선택 사항).
    :param priority: 태스크의 우선순위 (1-5, 숫자가 낮을수록 높음, 선택 사항).
    :param due_date: 태스크의 마감일 (YYYY-MM-DD 형식의 문자열, 선택 사항).
    :param estimated_time_hours: 태스크를 완료하는 데 예상되는 시간 (시간 단위, 선택 사항).
    :param status: 태스크의 현재 상태 ('TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED' 중 하나, 기본값은 'TODO').
    :param project_id: 이 태스크가 속할 프로젝트의 고유 ID (선택 사항).
    :return: 생성된 태스크의 정보 (dict) 또는 에러 메시지.
    """
    payload = {
        "title": title,
        "description": description,
        "tags": tags,
        "priority": priority,
        "dueDate": due_date,
        "estimatedTimeHours": estimated_time_hours,
        "status": status,
        "projectId": project_id,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    return call_spring_api("POST", "/tasks/new", payload=payload, jwt_token=jwt_token)


@tool
def get_all_tasks(jwt_token: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    현재 사용자의 모든 태스크를 조회합니다.
    이 도구는 '내 모든 태스크를 보여줘'와 같은 요청에 사용됩니다.

    :return: 모든 태스크 목록 (List[dict]) 또는 에러 메시지.
    """
    return call_spring_api("GET", "/tasks/all", jwt_token=jwt_token)


@tool
def get_single_task(task_id: int, jwt_token: Optional[str] = None) -> Dict[str, Any]:
    """
    특정 ID의 단일 태스크를 조회합니다.
    이 도구는 '123번 태스크는 뭐야?'와 같은 요청에 사용됩니다.

    :param task_id: 조회할 태스크의 고유 ID (필수).
    :return: 단일 태스크 정보 (dict) 또는 에러 메시지.
    """
    return call_spring_api("GET", f"/tasks/{task_id}", jwt_token=jwt_token)


@tool
def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    priority: Optional[int] = None,
    due_date: Optional[str] = None,
    estimated_time_hours: Optional[float] = None,
    status: Optional[TaskStatus] = None,
    project_id: Optional[int] = None,
    jwt_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    기존 태스크의 정보를 수정합니다. 수정할 필드만 입력하면 됩니다.
    이 도구는 '123번 태스크 제목을 '새로운 제목'으로 바꿔줘'와 같은 요청에 사용됩니다.

    :param task_id: 수정할 태스크의 고유 ID (필수).
    :param title: 태스크의 새로운 제목 (선택 사항).
    :param description: 태스크의 새로운 설명 (선택 사항).
    :param tags: 태스크 관련 새로운 콤마로 구분된 태그들 (선택 사항).
    :param priority: 태스크의 새로운 우선순위 (선택 사항).
    :param due_date: 태스크의 새로운 마감일 (YYYY-MM-DD 형식의 문자열, 선택 사항).
    :param estimated_time_hours: 태스크의 새로운 예상 소요 시간 (선택 사항).
    :param status: 태스크의 새로운 상태 (선택 사항).
    :param project_id: 이 태스크가 속할 새로운 프로젝트의 고유 ID (선택 사항).
    :return: 수정된 태스크의 정보 (dict) 또는 에러 메시지.
    """
    payload = {}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if tags is not None:
        payload["tags"] = tags
    if priority is not None:
        payload["priority"] = priority
    if due_date is not None:
        payload["dueDate"] = due_date
    if estimated_time_hours is not None:
        payload["estimatedTimeHours"] = estimated_time_hours
    if status is not None:
        payload["status"] = status
    if project_id is not None:
        payload["projectId"] = project_id

    if not payload:
        return {"error": "수정할 태스크 정보가 제공되지 않았습니다. 최소 하나 이상의 필드를 입력해야 합니다."}

    return call_spring_api("PUT", f"/tasks/{task_id}", payload=payload, jwt_token=jwt_token)


@tool
def delete_task(task_id: int, jwt_token: Optional[str] = None) -> Dict[str, Any]:
    """
    특정 태스크를 삭제합니다.
    이 도구는 '123번 태스크를 삭제해줘'와 같은 요청에 사용됩니다.

    :param task_id: 삭제할 태스크의 고유 ID (필수).
    :return: 성공 메시지 또는 에러 메시지.
    """
    return call_spring_api("DELETE", f"/tasks/{task_id}", jwt_token=jwt_token)


@tool
def update_task_status(task_id: int, status: TaskStatus, jwt_token: Optional[str] = None) -> Dict[str, Any]:
    """
    특정 태스크의 상태를 업데이트합니다.
    이 도구는 '123번 태스크를 완료 상태로 바꿔줘'와 같은 요청에 사용됩니다.

    :param task_id: 상태를 변경할 태스크의 고유 ID (필수).
    :param status: 태스크의 새로운 상태 ('TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED' 중 하나, 필수).
    :return: 업데이트된 태스크의 정보 (dict) 또는 에러 메시지.
    """
    payload = {"status": status}
    return call_spring_api("PATCH", f"/tasks/{task_id}/status", payload=payload, jwt_token=jwt_token)


@tool
def update_task_tags(task_id: int, tags: Optional[List[str]], jwt_token: Optional[str] = None) -> Dict[str, Any]:
    """
    특정 태스크의 태그를 업데이트합니다. 기존 태그는 새로운 태그 목록으로 교체됩니다.
    이 도구는 '123번 태스크에 '긴급', '회의' 태그를 추가해줘'와 같은 요청에 사용됩니다.
    태그를 완전히 제거하려면 빈 문자열을 입력하는 방식을 사용합니다.

    :param task_id: 태그를 변경할 태스크의 고유 ID (필수).
    :param tags: 태스크의 새로운 태그 목록 (List[str], 선택 사항. 빈 리스트를 넘기면 태그가 없는 상태가 됩니다. None은 허용되지 않습니다.).
    :return: 업데이트된 태스크의 정보 (dict) 또는 에러 메시지.
    """

    payload = {"tags": tags}
    return call_spring_api("PATCH", f"/tasks/{task_id}/tags", payload=payload, jwt_token=jwt_token)


@tool
def remove_task_tags(task_id: int, jwt_token: Optional[str] = None) -> Dict[str, Any]:
    """
    특정 태스크의 모든 태그를 제거합니다.
    이 도구는 '123번 태스크의 모든 태그를 삭제해줘'와 같은 요청에 사용됩니다.

    :param task_id: 태그를 제거할 태스크의 고유 ID (필수).
    :return: 업데이트된 태스크의 정보 (dict) 또는 에러 메시지.
    """
    # Spring 백엔드에 DELETE /api/mcp/tasks/{id}/tags 엔드포인트가 필요합니다.
    return call_spring_api("DELETE", f"/tasks/{task_id}/tags", jwt_token=jwt_token)


@tool
def update_task_schedule(
    task_id: int,
    due_date: Optional[str] = None, # YYYY-MM-DD
    priority: Optional[int] = None,
    jwt_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    특정 태스크의 마감일과 우선순위를 업데이트합니다.
    이 도구는 '123번 태스크 마감일을 내일로, 우선순위를 높여줘'와 같은 요청에 사용됩니다.

    :param task_id: 스케줄을 변경할 태스크의 고유 ID (필수).
    :param due_date: 태스크의 새로운 마감일 (YYYY-MM-DD 형식의 문자열, 선택 사항).
    :param priority: 태스크의 새로운 우선순위 (1-5, 숫자가 낮을수록 높음, 선택 사항).
    :return: 업데이트된 태스크의 정보 (dict) 또는 에러 메시지.
    """
    payload = {}
    if due_date is not None:
        payload["dueDate"] = due_date
    if priority is not None:
        payload["priority"] = priority
    
    if not payload:
        return {"error": "수정할 스케줄 정보가 제공되지 않았습니다. 최소 하나 이상의 필드를 입력해야 합니다."}

    return call_spring_api("PATCH", f"/tasks/{task_id}/schedule", payload=payload, jwt_token=jwt_token)
