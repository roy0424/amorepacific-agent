# 🚀 Docker 배포 가이드

Laneige Ranking Tracker를 Docker로 배포하는 완벽한 가이드입니다.

## 📋 목차

1. [사전 준비](#사전-준비)
2. [빠른 시작](#빠른-시작)
3. [상세 설정](#상세-설정)
4. [운영 가이드](#운영-가이드)
5. [문제 해결](#문제-해결)
6. [클라우드 배포](#클라우드-배포)

---

## 사전 준비

### 1. Docker 설치

**macOS**:
```bash
# Homebrew 사용
brew install --cask docker

# 또는 Docker Desktop 다운로드
# https://www.docker.com/products/docker-desktop
```

**Windows**:
- Docker Desktop 다운로드: https://www.docker.com/products/docker-desktop

**Linux**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### 2. Docker 설치 확인

```bash
docker --version
docker-compose --version
```

**예상 출력**:
```
Docker version 24.0.0, build ...
Docker Compose version v2.20.0
```

---

## 빠른 시작

### 1단계: API 키 설정

```bash
# .env 파일 생성
cp .env.example .env

# 편집기로 열기
nano .env  # 또는 vim, code 등
```

**필수 API 키**:
```env
YOUTUBE_API_KEY=AIzaSy-your-youtube-api-key-here
```

**선택 API 키** (프롬프트 테스터 사용 시):
```env
OPENAI_API_KEY=sk-your-api-key-here
```

### 2단계: Docker 배포

```bash
# 자동 배포 스크립트 실행
bash scripts/deploy_docker.sh
```

**실행 과정** (5-10분):
1. ✅ 환경 변수 확인
2. ✅ 기존 컨테이너 정리
3. ✅ Docker 이미지 빌드
4. ✅ 컨테이너 시작
5. ✅ 상태 확인

### 3단계: 접속 확인

**Prefect UI**: http://localhost:4200
- Flow 실행 내역 확인
- 스케줄 관리
- 실시간 로그

**프롬프트 테스터**: http://localhost:8501
- AI 프롬프트 테스트 (OPENAI_API_KEY 필요)

### 4단계: 데이터 수집 확인

```bash
# 컨테이너 내부에서 실행
docker exec laneige-tracker python scripts/check_data.py
```

---

## 상세 설정

### docker-compose.yml 커스터마이징

#### 포트 변경

```yaml
ports:
  - "5000:4200"  # Prefect UI를 5000번 포트로
  - "8502:8501"  # Streamlit을 8502번 포트로
```

#### 메모리 제한

```yaml
services:
  laneige-tracker:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

#### 재시작 정책

```yaml
restart: always  # 항상 재시작
restart: on-failure  # 실패 시만 재시작
restart: unless-stopped  # 수동 중지 전까지 재시작 (기본)
```

### 환경 변수 전체 목록

`.env` 파일에서 설정 가능한 모든 옵션:

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `YOUTUBE_API_KEY` | YouTube API 키 (필수) | - |
| `OPENAI_API_KEY` | OpenAI API 키 (선택) | - |
| `AMAZON_SCRAPE_INTERVAL_HOURS` | Amazon 수집 주기 | 1 |
| `PLAYWRIGHT_HEADLESS` | 헤드리스 모드 | true |
| `LOG_LEVEL` | 로그 레벨 | INFO |
| `DATABASE_URL` | 데이터베이스 경로 | postgresql+psycopg://laneige:laneige@localhost:5432/laneige_tracker |

---

## 운영 가이드

### 컨테이너 관리

#### 상태 확인
```bash
docker-compose ps
```

#### 로그 확인
```bash
# 실시간 로그 (Ctrl+C로 종료)
docker-compose logs -f

# 최근 100줄
docker-compose logs --tail=100

# 특정 서비스만
docker-compose logs laneige-tracker
```

#### 재시작
```bash
# 전체 재시작
docker-compose restart

# 이미지 재빌드 후 재시작
docker-compose up -d --build
```

#### 중지 및 삭제
```bash
# 중지 (컨테이너 유지)
docker-compose stop

# 중지 및 삭제
docker-compose down

# 볼륨까지 삭제 (데이터 초기화)
docker-compose down -v
```

### 데이터 백업

```bash
# 데이터 디렉토리 백업
tar -czf laneige-backup-$(date +%Y%m%d).tar.gz data/

# 복원
tar -xzf laneige-backup-20251220.tar.gz
```

### 데이터베이스 접근

```bash
# 컨테이너 내부 쉘 접속
docker exec -it laneige-tracker bash

# Python 스크립트 실행
docker exec laneige-tracker python scripts/check_data.py

# 리포트 생성
docker exec laneige-tracker python scripts/generate_team_report.py
```

### 자동 백업 스케줄

**cron 사용** (Linux/macOS):
```bash
# crontab 편집
crontab -e

# 매일 새벽 3시 백업 (추가)
0 3 * * * cd /path/to/laneige-ranking-tracker && tar -czf ~/backups/laneige-$(date +\%Y\%m\%d).tar.gz data/
```

---

## 문제 해결

### 문제 1: 컨테이너가 시작되지 않음

**증상**:
```
Error response from daemon: Container is not running
```

**해결**:
```bash
# 로그 확인
docker-compose logs

# 이미지 재빌드
docker-compose build --no-cache
docker-compose up -d
```

### 문제 2: Playwright 브라우저 오류

**증상**:
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**해결**:
```bash
# 이미지 재빌드 (브라우저 재설치)
docker-compose build --no-cache
docker-compose up -d
```

### 문제 3: 포트가 이미 사용 중

**증상**:
```
Error starting userland proxy: listen tcp4 0.0.0.0:4200: bind: address already in use
```

**해결**:
```bash
# 1. 사용 중인 프로세스 찾기
lsof -i :4200

# 2. 프로세스 종료
kill -9 <PID>

# 3. 또는 docker-compose.yml에서 포트 변경
ports:
  - "5000:4200"
```

### 문제 4: 데이터가 유지되지 않음

**해결**:
```bash
# docker-compose.yml에서 볼륨 확인
volumes:
  - ./data:/app/data  # 호스트 디렉토리 마운트

# 권한 확인
ls -la data/
chmod -R 755 data/
```

### 문제 5: API 키 오류

**증상**:
```
ValidationError: YOUTUBE_API_KEY - Field required
```

**해결**:
```bash
# .env 파일 확인
cat .env | grep YOUTUBE_API_KEY

# 컨테이너 재시작 (환경변수 재로드)
docker-compose restart
```

---

## 클라우드 배포

### AWS EC2

#### 1. EC2 인스턴스 생성

- AMI: Ubuntu 22.04 LTS
- 인스턴스 타입: t3.small 이상 (2 vCPU, 2 GiB)
- 스토리지: 30 GB 이상
- 보안 그룹:
  - SSH (22): 내 IP만
  - HTTP (80): 0.0.0.0/0
  - Custom TCP (4200): 0.0.0.0/0 (Prefect UI)

#### 2. 서버 접속 및 설정

```bash
# SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Git 클론
git clone https://github.com/your-repo/laneige-ranking-tracker.git
cd laneige-ranking-tracker

# .env 설정
nano .env

# 배포
bash scripts/deploy_docker.sh
```

#### 3. 도메인 연결 (선택)

```bash
# Nginx 설치
sudo apt-get install nginx

# Nginx 설정
sudo nano /etc/nginx/sites-available/laneige

# 내용:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:4200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# 활성화
sudo ln -s /etc/nginx/sites-available/laneige /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 4. HTTPS 설정 (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### GCP Compute Engine

#### 1. 인스턴스 생성

```bash
# gcloud CLI로 생성
gcloud compute instances create laneige-tracker \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-small \
  --boot-disk-size=30GB \
  --tags=http-server,https-server
```

#### 2. 배포 (AWS EC2와 동일)

### 비용 예상

**AWS EC2**:
- t3.small: $15-20/월
- 스토리지: $3/월
- 총: **$20-25/월**

**GCP Compute Engine**:
- e2-small: $13-18/월
- 스토리지: $3/월
- 총: **$18-23/월**

**무료 티어**:
- AWS: 12개월 t2.micro 무료 (충분함)
- GCP: 3개월 $300 크레딧

---

## 모니터링

### Docker Stats

```bash
# 실시간 리소스 사용량
docker stats laneige-tracker
```

### 자동 재시작 확인

```bash
# 재시작 횟수 확인
docker inspect laneige-tracker | grep RestartCount
```

### 헬스체크

docker-compose.yml에 포함됨:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:4200')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## 성능 최적화

### 1. 이미지 크기 줄이기

**현재**: ~2GB (Playwright 브라우저 포함)

**최적화**:
```dockerfile
# multi-stage build 사용
FROM python:3.11-slim AS builder
# ... 의존성 설치 ...

FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
```

### 2. 메모리 사용량 줄이기

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - MALLOC_TRIM_THRESHOLD_=100000
```

### 3. 로그 로테이션

```bash
# docker-compose.yml에 추가
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 다음 단계

배포 후:
1. ✅ Prefect UI 접속하여 Flow 실행 확인
2. ✅ 데이터 수집 확인 (`check_data.py`)
3. ✅ 12시간 후 이벤트 감지 확인
4. ✅ 팀 리포트 생성 (`generate_team_report.py`)
5. ✅ 프롬프트 테스터로 인사이트 품질 개선

**Phase 4 개발 시**:
- 이메일/Slack 알림 추가
- 대시보드 구축
- 자동 리포트 전송

---

## 도움말

**문제 발생 시**:
1. 로그 확인: `docker-compose logs -f`
2. 상태 확인: `docker-compose ps`
3. GitHub Issues: [링크]

**추가 문서**:
- `README.md` - 프로젝트 개요
- `QUICKSTART.md` - 빠른 시작 가이드
- `TEAM_MEETING_GUIDE.md` - 팀 회의 발표 가이드

---

Happy Deploying! 🚀
