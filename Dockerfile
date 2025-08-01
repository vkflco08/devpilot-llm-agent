# Dockerfile
# 공식 Python 이미지 사용
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# mysqlclient 설치를 위해 필요한 시스템 의존성 설치
# `build-essential`은 C 컴파일러 등 빌드 도구를 제공합니다.
# `default-libmysqlclient-dev`는 mysqlclient 빌드에 필요한 헤더 파일을 제공합니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY devpilot_agent/ devpilot_agent/

# 환경 변수 및 기타 설정 (필요시 주석 해제)
# COPY .env .env 
# ENV OPENAI_API_KEY=${OPENAI_API_KEY}
# ENV SPRING_BACKEND_URL=${SPRING_BACKEND_URL}

# CMD 명령어를 Uvicorn을 사용하여 FastAPI 앱을 실행하도록 변경
CMD ["uvicorn", "devpilot_agent.api:api_app", "--host", "0.0.0.0", "--port", "8000"]

# FastAPI 앱이 8000번 포트에서 실행될 것임을 노출
EXPOSE 8000
