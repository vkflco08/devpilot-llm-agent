import requests
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import json
import traceback

load_dotenv()

SPRING_BACKEND_URL = os.getenv("SPRING_BACKEND_URL")

def call_spring_api(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    jwt_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Spring 백엔드의 MCP API를 호출하는 내부 헬퍼 함수입니다.
    요청 시 X-User-ID 헤더를 포함할 수 있습니다.
    """
    if not SPRING_BACKEND_URL:
        return {"error": "SPRING_BACKEND_URL 환경 변수가 설정되지 않았습니다."}

    url = f"{SPRING_BACKEND_URL}/api/agent{path}"

    headers = {"Content-Type": "application/json"}

    if jwt_token is None:
        print("JWT token is required")
        return {"error": "JWT token is required"}
    
    headers["Authorization"] = f"Bearer {jwt_token}"
    
    print(f"Calling Spring API: {method} {url} with data: {payload} and headers: {headers}")
    
    try:
        response = None
        if method == "POST":
            response = requests.post(url, headers=headers, json=payload)
        elif method == "GET":
            response = requests.get(url, headers=headers, params=payload)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=payload)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, json=payload)
        else:
            return {"error": f"지원되지 않는 HTTP 메서드: {method}"}

        if response.status_code == 204:
            return {"message": "요청이 성공적으로 처리되었으나 반환할 내용이 없습니다.", "status_code": 204}
        
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            response_text = response.text.strip()
            if not response_text:
                response_text = "응답 내용: 없음"
            print(f"JSONDecodeError: Response was not valid JSON. Status: {response.status_code}, Content: '{response_text}'")
            response.raise_for_status()
            return {"error": f"API 응답 파싱 실패: {response_text}", "status_code": response.status_code}

        response.raise_for_status()

        return response_json

    except requests.exceptions.HTTPError as http_err:
        error_detail = response.text if response else "응답 내용: 없음"
        if response and response.status_code == 401:
            return {"error": f"API 호출 실패: 401 인증 오류. 백엔드 보안 설정을 확인하세요. URL: {url}. 응답 내용: {error_detail}", "status_code": 401}
        
        print(f"HTTP error occurred: {http_err} - Detail: {error_detail}")
        return {"error": f"API 호출 실패: {http_err}. 응답 내용: {error_detail}", "status_code": response.status_code if response else 500}
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
        return {"error": f"Spring 백엔드에 연결할 수 없습니다. URL: {SPRING_BACKEND_URL}", "status_code": 503}
    except Exception as err:
        traceback.print_exc()
        print(f"Other error occurred during API call: {err}")
        return {"error": f"API 호출 중 알 수 없는 오류 발생: {err}", "status_code": 500}
