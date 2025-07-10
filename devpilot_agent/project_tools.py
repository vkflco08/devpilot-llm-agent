import requests
import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import Optional, Literal, List, Dict, Any

load_dotenv()
SPRING_BACKEND_URL = os.getenv("SPRING_BACKEND_URL")

ProjectStatus = Literal["ACTIVE", "ARCHIVED", "COMPLETED"] # Spring과 동일하게 정의

# 공통 API 호출 로직 (중복 제거)
def _call_spring_api(method: str, path: str, payload: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not SPRING_BACKEND_URL:
        return {"error": "SPRING_BACKEND_URL 환경 변수가 설정되지 않았습니다."}
    
    url = f"{SPRING_BACKEND_URL}/api/mcp{path}" # /api/mcp 접두사는 고정
    
    try:
        if method.upper() == "POST":
            response = requests.post(url, json=payload)
        elif method.upper() == "GET":
            response = requests.get(url, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, json=payload)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            return {"error": f"지원하지 않는 HTTP 메소드: {method}"}
            
        response.raise_for_status() # HTTP 4xx/5xx 에러 발생 시 예외 처리
        return response.json() if response.content else {"message": "Success"} # DELETE 요청 등 응답 바디 없을 수 있음
    except requests.exceptions.ConnectionError:
        return {"error": f"Spring 백엔드에 연결할 수 없습니다. URL: {SPRING_BACKEND_URL}"}
    except requests.exceptions.Timeout:
        return {"error": "Spring 백엔드 응답 시간 초과."}
    except requests.exceptions.RequestException as e:
        return {"error": f"API 호출 실패: {e}. 응답 내용: {response.text if response else '없음'}"}


@tool
def create_project(
    project_name: str,
    project_description: Optional[str] = None,
    project_status: ProjectStatus = "ACTIVE"
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
    return _call_spring_api("POST", "/projects/new", payload=payload)


@tool
def get_all_projects_with_tasks() -> List[Dict[str, Any]]:
    """
    현재 사용자의 모든 프로젝트와 그에 속한 태스크들을 조회합니다.
    :return: 프로젝트와 태스크 목록 (List[dict]) 또는 에러 메시지.
    """
    return _call_spring_api("GET", "/projects/mypage")


@tool
def get_dashboard_projects() -> List[Dict[str, Any]]:
    """
    현재 사용자의 진행 중인 프로젝트와 그에 속한 태스크들을 조회합니다.
    :return: 진행 중인 프로젝트 목록 (List[dict]) 또는 에러 메시지.
    """
    return _call_spring_api("GET", "/projects/dashboard")


@tool
def get_single_project_with_tasks(project_id: int) -> Dict[str, Any]:
    """
    특정 ID의 단일 프로젝트와 그에 속한 태스크들을 조회합니다.
    :param project_id: 조회할 프로젝트의 고유 ID (필수).
    :return: 단일 프로젝트 정보 (dict) 또는 에러 메시지.
    """
    return _call_spring_api("GET", f"/projects/{project_id}")


@tool
def update_project(
    project_id: int,
    project_name: Optional[str] = None,
    project_description: Optional[str] = None,
    project_status: Optional[ProjectStatus] = None
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

    return _call_spring_api("PUT", f"/projects/{project_id}", payload=payload)


@tool
def delete_project(project_id: int) -> Dict[str, Any]:
    """
    특정 프로젝트를 삭제합니다. 프로젝트와 관련된 모든 태스크도 함께 삭제됩니다.
    :param project_id: 삭제할 프로젝트의 고유 ID (필수).
    :return: 성공 메시지 또는 에러 메시지.
    """
    return _call_spring_api("DELETE", f"/projects/{project_id}")

# --- Tool 테스트 코드 (tools.py 파일 하단에 추가) ---
if __name__ == "__main__":
    print("--- project_tools.py 테스트 시작 ---")
    
    # 환경 변수 설정 (테스트를 위해 명시적으로 설정, 실제 실행 환경에서는 .env 로드)
    # 반드시 Spring 백엔드가 http://localhost:8080 에서 실행 중이어야 합니다!
    os.environ["SPRING_BACKEND_URL"] = "http://localhost:8080" 

    test_project_id = None # 테스트를 위해 생성된 프로젝트 ID를 저장할 변수

    # --- 1. 프로젝트 생성 테스트 ---
    print("\n[테스트 1] '새로운 LLM 통합 프로젝트' 생성 (필수 필드)")
    create_result = create_project(project_name="LLM 통합 테스트 프로젝트", project_description="LLM Tool 연동 테스트용")
    print(f"생성 결과: {create_result}")
    if "id" in create_result:
        test_project_id = create_result["id"]
        print(f"생성된 프로젝트 ID: {test_project_id}")
        assert isinstance(test_project_id, int) and test_project_id > 0, "테스트 1 실패: 유효한 프로젝트 ID가 없습니다."
    else:
        print("테스트 1 실패: 프로젝트 생성 실패. 더 이상 테스트를 진행할 수 없습니다.")
        exit() # 프로젝트 생성 실패 시 이후 테스트는 의미가 없으므로 종료

    # --- 2. 모든 프로젝트 조회 테스트 ---
    print("\n[테스트 2] 모든 프로젝트 조회 ('/mypage')")
    all_projects = get_all_projects_with_tasks()
    print(f"모든 프로젝트 결과: {all_projects}")
    assert isinstance(all_projects, list), "테스트 2 실패: 결과가 리스트가 아닙니다."
    # 생성된 프로젝트가 목록에 포함되어 있는지 간단히 확인
    found_created = any(p.get("id") == test_project_id for p in all_projects if isinstance(p, dict))
    assert found_created, "테스트 2 실패: 생성된 프로젝트가 목록에 없습니다."


    # --- 3. 대시보드 프로젝트 조회 테스트 (진행중) ---
    print("\n[테스트 3] 대시보드 프로젝트 조회 ('/dashboard')")
    dashboard_projects = get_dashboard_projects()
    print(f"대시보드 프로젝트 결과: {dashboard_projects}")
    assert isinstance(dashboard_projects, list), "테스트 3 실패: 결과가 리스트가 아닙니다."
    # 진행 중인 프로젝트만 있는지 추가적인 확인 로직이 필요할 수 있습니다 (현재는 단순히 리스트인지 확인)


    # --- 4. 단일 프로젝트 조회 테스트 ---
    print(f"\n[테스트 4] 단일 프로젝트 조회 (ID: {test_project_id})")
    single_project = get_single_project_with_tasks(project_id=test_project_id)
    print(f"단일 프로젝트 결과: {single_project}")
    assert "id" in single_project and single_project["id"] == test_project_id, "테스트 4 실패: 단일 프로젝트 조회 오류."
    assert "projectName" in single_project, "테스트 4 실패: 프로젝트 이름이 없습니다."


    # --- 5. 프로젝트 수정 테스트 ---
    print(f"\n[테스트 5] 프로젝트 수정 (ID: {test_project_id})")
    updated_name = "LLM 통합 프로젝트_수정됨"
    updated_description = "설명도 변경되었습니다."
    updated_status = "COMPLETED"
    update_result = update_project(
        project_id=test_project_id,
        project_name=updated_name,
        project_description=updated_description,
        project_status=updated_status
    )
    print(f"수정 결과: {update_result}")
    assert "id" in update_result and update_result["id"] == test_project_id, "테스트 5 실패: 수정된 프로젝트 ID가 다릅니다."
    assert update_result.get("projectName") == updated_name, "테스트 5 실패: 프로젝트 이름이 수정되지 않았습니다."
    assert update_result.get("projectDescription") == updated_description, "테스트 5 실패: 프로젝트 설명이 수정되지 않았습니다."
    assert update_result.get("projectStatus") == updated_status, "테스트 5 실패: 프로젝트 상태가 수정되지 않았습니다."

    # 수정된 내용으로 다시 단일 조회하여 최종 확인
    print(f"\n[테스트 5-1] 수정 후 단일 프로젝트 다시 조회 (ID: {test_project_id})")
    re_check_project = get_single_project_with_tasks(project_id=test_project_id)
    print(f"재확인 결과: {re_check_project}")
    assert re_check_project.get("projectName") == updated_name, "테스트 5-1 실패: 수정된 이름이 반영되지 않았습니다."
    assert re_check_project.get("projectDescription") == updated_description, "테스트 5-1 실패: 수정된 설명이 반영되지 않았습니다."
    assert re_check_project.get("projectStatus") == updated_status, "테스트 5-1 실패: 수정된 상태가 반영되지 않았습니다."


    # --- 6. 프로젝트 삭제 테스트 ---
    print(f"\n[테스트 6] 프로젝트 삭제 (ID: {test_project_id})")
    delete_result = delete_project(project_id=test_project_id)
    print(f"삭제 결과: {delete_result}")
    assert "error" not in delete_result and delete_result.get("status_code") in [200, 204], "테스트 6 실패: 프로젝트 삭제 오류."

    # 삭제 후 다시 단일 조회하여 존재하지 않는지 확인
    print(f"\n[테스트 6-1] 삭제 후 단일 프로젝트 다시 조회 (ID: {test_project_id}, 예상 실패)")
    try:
        # 삭제된 프로젝트 조회 시 404 Not Found (또는 적절한 에러)가 예상됨
        deleted_check = get_single_project_with_tasks(project_id=test_project_id)
        print(f"삭제 후 조회 결과: {deleted_check}")
        # 이 시점에서 오류가 발생해야 하므로, 오류가 발생하지 않으면 테스트 실패
        assert "error" in deleted_check, "테스트 6-1 실패: 삭제된 프로젝트가 여전히 조회됩니다."
    except requests.exceptions.RequestException as e:
        print(f"예상대로 에러 발생: {e}") # 예상된 에러 발생 (e.g. 404 Not Found)


    print("\n--- project_tools.py 모든 테스트 완료 ---")