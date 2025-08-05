import requests
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SPRING_BACKEND_URL = os.getenv("SPRING_BACKEND_URL")

def call_spring_api(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Spring 백엔드의 MCP API를 호출하는 내부 헬퍼 함수입니다.
    요청 시 X-User-ID 헤더를 포함할 수 있습니다.
    """
    if not SPRING_BACKEND_URL:
        return {"error": "SPRING_BACKEND_URL 환경 변수가 설정되지 않았습니다."}

    url = f"{SPRING_BACKEND_URL}/api/agent{path}"

    headers = {}
    headers["Content-Type"] = "application/json"

    if user_id is not None:
        headers["X-User-ID"] = str(user_id)

    try:
        if method.upper() == "POST":
            response = requests.post(url, json=payload, headers=headers)
        elif method.upper() == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=payload, headers=headers)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return {"error": f"지원하지 않는 HTTP 메소드: {method}"}

        response.raise_for_status()

        return response.json() if response.content else {"message": "Success", "status_code": response.status_code}

    except requests.exceptions.ConnectionError:
        return {"error": f"Spring 백엔드에 연결할 수 없습니다. URL: {SPRING_BACKEND_URL}"}
    except requests.exceptions.Timeout:
        return {"error": "Spring 백엔드 응답 시간 초과."}
    except requests.exceptions.RequestException as e:
        return {"error": f"API 호출 실패: {e}. 응답 내용: {response.text if response else '없음'}"}