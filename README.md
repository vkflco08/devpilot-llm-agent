# 🤖 DevPilot LLM Agent

LangGraph 기반의 프로젝트 및 태스크 관리 대화형 AI 에이전트입니다.

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.12-blue)
![Framework](https://img.shields.io/badge/Framework-FastAPI-009688)

---

## ✨ 주요 기능

-   **대화형 인터페이스**: 사용자의 자연어 요청을 이해하고 프로젝트와 태스크를 관리합니다.
-   **프로젝트 관리**: 프로젝트 생성, 조회, 수정, 삭제 기능을 제공합니다.
-   **태스크 관리**: 태스크 생성, 상태 변경, 태그 수정 등 다양한 관리 기능을 수행합니다.
-   **도구(Tool) 사용**: Spring Boot로 구현된 백엔드 API를 도구로 사용하여 실제 데이터와 상호작용합니다.

---

## 🏗️ 아키텍처

이 에이전트는 다음과 같은 흐름으로 동작합니다.

```
사용자 요청 -> [ FastAPI API 서버 ] -> [ LangGraph 에이전트 ] -> [ Tools (API 호출) ] -> [ Spring Boot 백엔드 ]
```

-   **FastAPI**: 에이전트를 외부로 노출하는 API 서버 역할을 합니다.
-   **LangGraph**: LLM의 추론 흐름을 제어하여, 사용자의 요청을 해결하기 위한 계획을 세우고 도구를 실행합니다.
-   **Tools**: `project_tools.py`와 `task_tools.py`에 정의된 함수들이며, 실제로는 Spring Boot 백엔드의 API를 호출합니다.

---

## 🚀 시작하기

### 사전 요구사항

-   Python 3.12
-   Docker
-   실행 중인 [DevPilot Spring Boot Backend](https://github.com/vkflco08/devpilot-backend)

---

## 🚢 배포 (CI/CD)

이 프로젝트는 Jenkins와 Kubernetes(Kustomize)를 이용한 GitOps 워크플로우를 통해 자동 배포됩니다.

1.  **CI (Continuous Integration)** - `devpilot-agent-build`
    -   `devpilot-llm-agent` 레포지토리의 `main` 브랜치에 코드가 푸시되면 Jenkins 파이프라인이 실행됩니다.
    -   파이프라인은 `Dockerfile`을 사용하여 애플리케이션을 도커 이미지로 빌드합니다.
    -   빌드된 이미지는 고유한 태그와 함께 Docker Hub에 푸시됩니다.

2.  **CD (Continuous Deployment)** - `devpilot-agent-deploy`
    -   CI 파이프라인이 성공하면 CD 파이프라인을 트리거합니다.
    -   CD 파이프라인은 [GitOps 배포 레포지토리](https://github.com/vkflco08/devpilot-k8s-app)에 접속합니다.
    -   `overlays/prod/agent/kustomization.yaml` 파일의 이미지 태그를 새로 빌드된 이미지의 태그로 업데이트하고 커밋/푸시합니다.
    -   Kubernetes 클러스터의 GitOps 도구(ArgoCD 등)가 배포 레포의 변경 사항을 감지하여 새로운 버전의 에이전트를 자동으로 배포합니다.
