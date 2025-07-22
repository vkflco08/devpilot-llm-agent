# Dockerfile
# 공식 Python 이미지 사용
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY devpilot_agent/ devpilot_agent/
# .env 파일도 컨테이너 내부로 복사 (주의: 민감 정보는 K8s Secret 사용 권장)
# COPY .env .env 

# 환경 변수 설정 (Kubernetes Secrets으로 대체될 예정이지만, 개발/테스트용으로 포함)
# ENV OPENAI_API_KEY=${OPENAI_API_KEY}
# ENV SPRING_BACKEND_URL=${SPRING_BACKEND_URL}

# ✨ CMD 명령어를 Uvicorn을 사용하여 FastAPI 앱을 실행하도록 변경
# devpilot_agent.api:api_app 은 devpilot_agent 폴더의 api.py 파일에서 api_app 객체를 실행하라는 의미
CMD ["uvicorn", "devpilot_agent.api:api_app", "--host", "0.0.0.0", "--port", "8000"]

# FastAPI 앱이 8000번 포트에서 실행될 것임을 노출
EXPOSE 8000
