# Laneige Ranking Tracker - Docker Image
FROM python:3.13-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 및 Playwright 필수 라이브러리 설치
RUN apt-get update && apt-get install -y \
    git \
    wget \
    gnupg \
    build-essential \
    g++ \
    gcc \
    make \
    # Playwright 의존성 (폰트 제외)
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libdrm2 \
    libxkbcommon0 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Playwright 브라우저 설치 (Amazon 스크래핑용)
RUN playwright install chromium

# 애플리케이션 코드 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p data/logs data/backups data/reports data/database

# 환경변수 설정
ENV PYTHONUNBUFFERED=1
ENV PREFECT_API_URL=http://prefect-server:4200/api
ENV PREFECT_WORK_POOL_NAME=default-process
ENV PREFECT_WORK_QUEUE_NAME=default
ENV PREFECT_DEPLOY_IMAGE=laneige-tracker:latest
ENV PREFECT_USE_SERVE=true

# 포트 노출
# 4200: Prefect UI
# 8501: Streamlit (프롬프트 테스터)
# 8502: Streamlit (DB 뷰어)
EXPOSE 4200 8501 8502

# 기본 명령어 (docker-compose에서 오버라이드)
CMD ["python", "scripts/start_all.py"]
