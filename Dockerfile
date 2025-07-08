# Dockerfile
# 공식 Python 이미지 사용
FROM python:3.9-slim-buster

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY devpilot_agent/ devpilot_agent/
# .env 파일도 컨테이너 내부로 복사 (주의: 민감 정보는 K8s Secret 사용 권장)
COPY .env .env 

# 환경 변수 설정 (Kubernetes Secrets으로 대체될 예정이지만, 개발/테스트용으로 포함)
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV SPRING_BACKEND_URL=${SPRING_BACKEND_URL}

# 명령 실행 권한 설정
# CMD [ "python", "-m", "uvicorn", "devpilot_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
# LangGraph 앱을 API로 노출할 경우 Uvicorn 같은 ASGI 서버 필요.
# 여기서는 임시로 main.py 스크립트 직접 실행 예시.
# 실제 서비스에서는 FastAPI 등을 사용하여 API 엔드포인트를 만들고 Uvicorn으로 실행합니다.
CMD ["python", "devpilot_agent/main.py"]