import requests
import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import Optional, Literal, List, Dict, Any
from devpilot_agent.utils.api_caller import call_spring_api

# 환경 변수 로드 (이 파일이 단독으로 실행될 때를 위함)
load_dotenv()

# TaskStatus 열거형을 Python에서 사용할 수 있도록 정의
# 실제 Spring의 TaskStatus와 정확히 일치해야 합니다.
TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE", "BLOCKED"]

# --- 태스크 CRUD Tools ---

@tool
def create_task(
    title: str,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    priority: Optional[int] = None, # Spring에서 default 3이므로 Optional로
    due_date: Optional[str] = None, # LocalDate를 문자열(YYYY-MM-DD)로 처리
    estimated_time_hours: Optional[float] = None, # Double을 float로
    status: TaskStatus = "TODO", # Spring에서 default TODO이므로 기본값 설정
    # parent_id: Optional[int] = None, # 현재 TaskCreateRequest에 parentId가 주석 처리되어 있어 제외
    project_id: Optional[int] = None,
    request_user_id: Optional[int] = None,
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
        "dueDate": due_date, # LocalDate는 문자열로 전달
        "estimatedTimeHours": estimated_time_hours,
        "status": status,
        "projectId": project_id,
    }
    # payload에서 None인 값들을 제거하여 Spring의 Optional<Type> 매핑을 돕습니다.
    payload = {k: v for k, v in payload.items() if v is not None}

    return call_spring_api("POST", "/tasks/new", payload=payload, user_id_for_request=request_user_id)


@tool
def get_all_tasks(request_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    현재 사용자의 모든 태스크를 조회합니다.
    이 도구는 '내 모든 태스크를 보여줘'와 같은 요청에 사용됩니다.

    :return: 모든 태스크 목록 (List[dict]) 또는 에러 메시지.
    """
    return call_spring_api("GET", "/tasks/all", user_id_for_request=request_user_id)


@tool
def get_single_task(task_id: int, request_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    특정 ID의 단일 태스크를 조회합니다.
    이 도구는 '123번 태스크는 뭐야?'와 같은 요청에 사용됩니다.

    :param task_id: 조회할 태스크의 고유 ID (필수).
    :return: 단일 태스크 정보 (dict) 또는 에러 메시지.
    """
    return call_spring_api("GET", f"/tasks/{task_id}", user_id_for_request=request_user_id)


@tool
def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    priority: Optional[int] = None,
    due_date: Optional[str] = None, # LocalDate를 문자열(YYYY-MM-DD)로 처리
    estimated_time_hours: Optional[float] = None,
    status: Optional[TaskStatus] = None,
    # parent_id: Optional[int] = None,
    project_id: Optional[int] = None,
    request_user_id: Optional[int] = None,
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
    # if parent_id is not None:
    #     payload["parentId"] = parent_id # TaskUpdateRequest에 parentId가 있다면 활성화

    if not payload:
        return {"error": "수정할 태스크 정보가 제공되지 않았습니다. 최소 하나 이상의 필드를 입력해야 합니다."}

    return call_spring_api("PUT", f"/tasks/{task_id}", payload=payload, user_id_for_request=request_user_id)


@tool
def delete_task(task_id: int, request_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    특정 태스크를 삭제합니다.
    이 도구는 '123번 태스크를 삭제해줘'와 같은 요청에 사용됩니다.

    :param task_id: 삭제할 태스크의 고유 ID (필수).
    :return: 성공 메시지 또는 에러 메시지.
    """
    return call_spring_api("DELETE", f"/tasks/{task_id}", user_id_for_request=request_user_id)


@tool
def update_task_status(task_id: int, status: TaskStatus, request_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    특정 태스크의 상태를 업데이트합니다.
    이 도구는 '123번 태스크를 완료 상태로 바꿔줘'와 같은 요청에 사용됩니다.

    :param task_id: 상태를 변경할 태스크의 고유 ID (필수).
    :param status: 태스크의 새로운 상태 ('TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED' 중 하나, 필수).
    :return: 업데이트된 태스크의 정보 (dict) 또는 에러 메시지.
    """
    payload = {"status": status}
    return call_spring_api("PATCH", f"/tasks/{task_id}/status", payload=payload, user_id_for_request=request_user_id)


@tool
def update_task_tags(task_id: int, tags: Optional[List[str]], request_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    특정 태스크의 태그를 업데이트합니다. 기존 태그는 새로운 태그 목록으로 교체됩니다.
    이 도구는 '123번 태스크에 '긴급', '회의' 태그를 추가해줘'와 같은 요청에 사용됩니다.
    태그를 완전히 제거하려면 빈 문자열을 입력하는 방식을 사용합니다.

    :param task_id: 태그를 변경할 태스크의 고유 ID (필수).
    :param tags: 태스크의 새로운 태그 목록 (List[str], 선택 사항. 빈 리스트를 넘기면 태그가 없는 상태가 됩니다. None은 허용되지 않습니다.).
    :return: 업데이트된 태스크의 정보 (dict) 또는 에러 메시지.
    """

    payload = {"tags": tags}
    return call_spring_api("PATCH", f"/tasks/{task_id}/tags", payload=payload, user_id_for_request=request_user_id)


@tool
def remove_task_tags(task_id: int, request_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    특정 태스크의 모든 태그를 제거합니다.
    이 도구는 '123번 태스크의 모든 태그를 삭제해줘'와 같은 요청에 사용됩니다.

    :param task_id: 태그를 제거할 태스크의 고유 ID (필수).
    :return: 업데이트된 태스크의 정보 (dict) 또는 에러 메시지.
    """
    # Spring 백엔드에 DELETE /api/mcp/tasks/{id}/tags 엔드포인트가 필요합니다.
    return call_spring_api("DELETE", f"/tasks/{task_id}/tags", user_id_for_request=request_user_id)


@tool
def update_task_schedule(
    task_id: int,
    due_date: Optional[str] = None, # YYYY-MM-DD
    priority: Optional[int] = None,
    request_user_id: Optional[int] = None,
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

    return call_spring_api("PATCH", f"/tasks/{task_id}/schedule", payload=payload, user_id_for_request=request_user_id)


# --- 테스트 코드 (파일 하단에 추가) ---
if __name__ == "__main__":
    print("--- task_tools.py 테스트 시작 ---")
    
    # 환경 변수 설정 (테스트를 위해 명시적으로 설정, 실제 실행 환경에서는 .env 로드)
    # 반드시 Spring 백엔드가 http://localhost:8080 에서 실행 중이어야 합니다!
    os.environ["SPRING_BACKEND_URL"] = "http://localhost:8080" 

    test_task_id = None # 테스트를 위해 생성된 태스크 ID를 저장할 변수
    test_project_id_for_task = None # 태스크를 특정 프로젝트에 연결할 경우 필요 (옵션)
    
    # 먼저 프로젝트를 하나 생성하여 태스크 테스트에 사용할 수 있도록 합니다. (옵션)
    print("\n[전제 조건] 태스크 테스트를 위해 프로젝트 생성 시도...")
    try:
        from devpilot_agent.project_tools import create_project as _create_project
        project_result = _create_project(project_name="태스크 테스트용 프로젝트", project_description="임시 프로젝트")
        if "id" in project_result:
            test_project_id_for_task = project_result["id"]
            print(f"테스트용 프로젝트 ID: {test_project_id_for_task}")
        else:
            print(f"테스트용 프로젝트 생성 실패: {project_result.get('error', '알 수 없는 오류')}")
            # 프로젝트 생성 실패 시에도 태스크 테스트는 진행할 수 있도록 (projectId 없이)
    except ImportError:
        print("devpilot_agent.project_tools를 임포트할 수 없습니다. 프로젝트 없는 태스크 테스트만 진행합니다.")


    # --- 1. 태스크 생성 테스트 ---
    print("\n[테스트 1] '백엔드 API 구현' 태스크 생성")
    create_result = create_task(
        title="백엔드 API 구현",
        description="프로젝트 관리 API 개발",
        tags="backend,api",
        priority=1,
        due_date="2025-07-30",
        estimated_time_hours=40.0,
        status="TODO",
        project_id=test_project_id_for_task # 프로젝트 ID가 있다면 연결
    )
    print(f"생성 결과: {create_result}")
    if "id" in create_result:
        test_task_id = create_result["id"]
        print(f"생성된 태스크 ID: {test_task_id}")
        assert isinstance(test_task_id, int) and test_task_id > 0, "테스트 1 실패: 유효한 태스크 ID가 없습니다."
    else:
        print("테스트 1 실패: 태스크 생성 실패. 더 이상 테스트를 진행할 수 없습니다.")
        exit() # 태스크 생성 실패 시 이후 테스트는 의미가 없으므로 종료

    # --- 2. 전체 태스크 조회 테스트 ---
    print("\n[테스트 2] 모든 태스크 조회 ('/all')")
    all_tasks = get_all_tasks()
    print(f"모든 태스크 결과: {all_tasks}")
    assert isinstance(all_tasks, list), "테스트 2 실패: 결과가 리스트가 아닙니다."
    # 생성된 태스크가 목록에 포함되어 있는지 간단히 확인
    found_created = any(t.get("id") == test_task_id for t in all_tasks if isinstance(t, dict))
    assert found_created, "테스트 2 실패: 생성된 태스크가 목록에 없습니다."


    # --- 3. 단일 태스크 조회 테스트 ---
    print(f"\n[테스트 3] 단일 태스크 조회 (ID: {test_task_id})")
    single_task = get_single_task(task_id=test_task_id)
    print(f"단일 태스크 결과: {single_task}")
    assert "id" in single_task and single_task["id"] == test_task_id, "테스트 3 실패: 단일 태스크 조회 오류."
    assert "title" in single_task, "테스트 3 실패: 태스크 제목이 없습니다."


    # --- 4. 태스크 수정 테스트 ---
    print(f"\n[테스트 4] 태스크 수정 (ID: {test_task_id})")
    updated_title = "백엔드 API 개발 완료"
    updated_status = "DONE"
    updated_priority = 5
    update_result = update_task(
        task_id=test_task_id,
        title=updated_title,
        status=updated_status,
        priority=updated_priority
    )
    print(f"수정 결과: {update_result}")
    assert "id" in update_result and update_result["id"] == test_task_id, "테스트 4 실패: 수정된 태스크 ID가 다릅니다."
    assert update_result.get("title") == updated_title, "테스트 4 실패: 태스크 제목이 수정되지 않았습니다."
    assert update_result.get("status") == updated_status, "테스트 4 실패: 태스크 상태가 수정되지 않았습니다."
    assert update_result.get("priority") == updated_priority, "테스트 4 실패: 태스크 우선순위가 수정되지 않았습니다."

    # 수정된 내용으로 다시 단일 조회하여 최종 확인
    print(f"\n[테스트 4-1] 수정 후 단일 태스크 다시 조회 (ID: {test_task_id})")
    re_check_task = get_single_task(task_id=test_task_id)
    print(f"재확인 결과: {re_check_task}")
    assert re_check_task.get("title") == updated_title, "테스트 4-1 실패: 수정된 제목이 반영되지 않았습니다."
    assert re_check_task.get("status") == updated_status, "테스트 4-1 실패: 수정된 상태가 반영되지 않았습니다."


    if test_task_id: # 태스크 생성이 성공했을 경우에만 패치 테스트 진행
        print("\n--- 태스크 특정 속성 업데이트 Tools 테스트 시작 ---")

        # --- 6. 태스크 상태 업데이트 테스트 ---
        print(f"\n[테스트 6] 태스크 상태 업데이트 (ID: {test_task_id})")
        status_update_result = update_task_status(task_id=test_task_id, status="IN_PROGRESS")
        print(f"상태 업데이트 결과: {status_update_result}")
        assert "id" in status_update_result and status_update_result.get("status") == "IN_PROGRESS", "테스트 6 실패: 상태 업데이트 오류."

        # --- 7. 태스크 태그 업데이트 테스트 ---
        print(f"\n[테스트 7] 태스크 태그 업데이트 (ID: {test_task_id})")
        tags_update_result = update_task_tags(task_id=test_task_id, tags="urgent,review")
        print(f"태그 업데이트 결과: {tags_update_result}")
        assert "id" in tags_update_result and "urgent,review" in tags_update_result.get("tags", ""), "테스트 7 실패: 태그 업데이트 오류."

        # --- 8. 태스크 스케줄 업데이트 테스트 ---
        print(f"\n[테스트 8] 태스크 스케줄 업데이트 (ID: {test_task_id})")
        schedule_update_result = update_task_schedule(task_id=test_task_id, due_date="2025-08-15", priority=1)
        print(f"스케줄 업데이트 결과: {schedule_update_result}")
        assert "id" in schedule_update_result and schedule_update_result.get("dueDate") == "2025-08-15", "테스트 8 실패: 스케줄 업데이트 오류."
        assert schedule_update_result.get("priority") == 1, "테스트 8 실패: 우선순위 업데이트 오류."

        # --- 9. 태스크 예상 소요 시간 업데이트 테스트 ---
        print(f"\n[테스트 9] 태스크 예상 소요 시간 업데이트 (ID: {test_task_id})")
        time_update_result = update_task_time(task_id=test_task_id, estimated_time_hours=10.5)
        print(f"시간 업데이트 결과: {time_update_result}")
        assert "id" in time_update_result and time_update_result.get("estimatedTimeHours") == 10.5, "테스트 9 실패: 예상 소요 시간 업데이트 오류."
        
        print("\n--- 태스크 특정 속성 업데이트 Tools 테스트 완료 ---")
        
        # 마지막으로, 모든 패치 테스트 후 태스크 삭제를 다시 시도하여 정리
        print(f"\n[정리] 테스트 태스크 최종 삭제 (ID: {test_task_id})")
        final_delete_result = delete_task(task_id=test_task_id)
        print(f"최종 삭제 결과: {final_delete_result}")
        assert "error" not in final_delete_result, "최종 정리 실패: 태스크 삭제 오류."
    else:
        print("\n태스크 생성 실패로 인해 특정 속성 업데이트 테스트는 건너뜝니다.")


    # --- 5. 태스크 삭제 테스트 ---
    print(f"\n[테스트 5] 태스크 삭제 (ID: {test_task_id})")
    delete_result = delete_task(task_id=test_task_id)
    print(f"삭제 결과: {delete_result}")
    assert "error" not in delete_result and delete_result.get("status_code") in [200, 204], "테스트 5 실패: 태스크 삭제 오류."

    # 삭제 후 다시 단일 조회하여 존재하지 않는지 확인
    print(f"\n[테스트 5-1] 삭제 후 단일 태스크 다시 조회 (ID: {test_task_id}, 예상 실패)")
    try:
        deleted_check = get_single_task(task_id=test_task_id)
        print(f"삭제 후 조회 결과: {deleted_check}")
        assert "error" in deleted_check, "테스트 5-1 실패: 삭제된 태스크가 여전히 조회됩니다."
    except requests.exceptions.RequestException as e:
        print(f"예상대로 에러 발생: {e}")


    # --- 테스트용 프로젝트 정리 (옵션) ---
    if test_project_id_for_task:
        print(f"\n[정리] 테스트용 프로젝트 삭제 (ID: {test_project_id_for_task})")
        try:
            from devpilot_agent.project_tools import delete_project as _delete_project
            cleanup_project_result = _delete_project(project_id=test_project_id_for_task)
            print(f"테스트용 프로젝트 삭제 결과: {cleanup_project_result}")
        except ImportError:
            print("프로젝트 삭제 도구를 임포트할 수 없어 테스트용 프로젝트 정리를 건너뜀.")


    print("\n--- task_tools.py 모든 테스트 완료 ---")