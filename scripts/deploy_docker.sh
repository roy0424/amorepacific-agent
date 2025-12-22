#!/bin/bash
# Docker 배포 스크립트

set -e  # 에러 발생 시 중단

echo "=================================="
echo "  🐳 Laneige Tracker Docker 배포"
echo "=================================="
echo

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "📂 작업 디렉토리: $PROJECT_ROOT"
echo

# 1. 환경 변수 확인
echo "1️⃣  환경 변수 확인 중..."
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다."
    echo "   .env.example을 복사하여 .env를 만들고 API 키를 설정하세요."
    exit 1
fi

# YouTube API 키 확인
if ! grep -q "YOUTUBE_API_KEY=.*[A-Za-z0-9]" .env; then
    echo "⚠️  YOUTUBE_API_KEY가 설정되지 않았습니다."
    echo "   계속하시겠습니까? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ 환경 변수 확인 완료"
echo

# 2. 기존 컨테이너 정리
echo "2️⃣  기존 컨테이너 정리 중..."
docker-compose down 2>/dev/null || true
echo "✅ 정리 완료"
echo

# 3. Docker 이미지 빌드
echo "3️⃣  Docker 이미지 빌드 중..."
echo "   (처음 실행 시 5-10분 소요됩니다)"
docker-compose build
echo "✅ 빌드 완료"
echo

# 4. 컨테이너 시작
echo "4️⃣  컨테이너 시작 중..."
docker-compose up -d
echo "✅ 시작 완료"
echo

# 5. 상태 확인
echo "5️⃣  상태 확인 중..."
sleep 5
docker-compose ps
echo

# 6. 로그 확인
echo "=================================="
echo "  ✅ 배포 완료!"
echo "=================================="
echo
echo "📊 Prefect UI: http://localhost:4200"
echo "🧪 프롬프트 테스터: http://localhost:8501"
echo
echo "📝 유용한 명령어:"
echo "  • 로그 확인: docker-compose logs -f"
echo "  • 상태 확인: docker-compose ps"
echo "  • 중지: docker-compose stop"
echo "  • 재시작: docker-compose restart"
echo "  • 종료 및 삭제: docker-compose down"
echo
echo "🔍 실시간 로그 보기:"
docker-compose logs -f --tail=50
