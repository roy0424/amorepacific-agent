#!/bin/bash
# Laneige Ranking Tracker - 원클릭 설치 스크립트
# 팀원들이 쉽게 Prefect 환경을 구축할 수 있도록 돕는 스크립트

set -e  # 에러 발생 시 중단

echo "========================================="
echo "Laneige Ranking Tracker 설치 시작"
echo "========================================="
echo ""

# 1. Python 버전 체크
echo "📌 Step 1/6: Python 버전 확인..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   ✓ Python $python_version 감지됨"
echo ""

# 2. 가상환경 생성
echo "📌 Step 2/6: 가상환경 생성..."
if [ -d ".venv" ]; then
    echo "   ⚠️  가상환경이 이미 존재합니다. 재사용합니다."
else
    python3 -m venv .venv
    echo "   ✓ 가상환경 생성 완료"
fi
echo ""

# 3. 가상환경 활성화
echo "📌 Step 3/6: 가상환경 활성화..."
source .venv/bin/activate
echo "   ✓ 가상환경 활성화됨"
echo ""

# 4. 의존성 설치
echo "📌 Step 4/6: 패키지 설치 중..."
echo "   (약 2-3분 소요됩니다)"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "   ✓ 패키지 설치 완료"
echo ""

# 5. Playwright 설치
echo "📌 Step 5/6: Playwright 브라우저 설치..."
playwright install chromium
echo "   ✓ Playwright 설치 완료"
echo ""

# 6. 환경 변수 설정
echo "📌 Step 6/6: 환경 변수 설정..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✓ .env 파일 생성됨"
    echo "   ⚠️  .env 파일을 열어서 필요한 API 키를 입력하세요:"
    echo "      - YOUTUBE_API_KEY (선택)"
    echo "      - APIFY_API_TOKEN (선택)"
    echo "      - OPENAI_API_KEY (선택)"
else
    echo "   ✓ .env 파일이 이미 존재합니다"
fi
echo ""

# 7. 데이터베이스 초기화
echo "========================================="
echo "📊 데이터베이스 초기화"
echo "========================================="
read -p "데이터베이스를 초기화하시겠습니까? (y/n): " init_db
if [ "$init_db" = "y" ] || [ "$init_db" = "Y" ]; then
    python scripts/init_db.py
    echo "   ✓ 데이터베이스 초기화 완료"
else
    echo "   ⏭️  데이터베이스 초기화 건너뜀"
    echo "   (나중에 'python scripts/init_db.py' 실행)"
fi
echo ""

# 8. 설치 완료
echo "========================================="
echo "✅ 설치 완료!"
echo "========================================="
echo ""
echo "다음 명령어로 시작하세요:"
echo ""
echo "  1. 가상환경 활성화 (터미널을 새로 열었을 때):"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Prefect 서버 시작 (터미널 1):"
echo "     python scripts/start_prefect.py"
echo ""
echo "  3. 데이터 수집 실행 (터미널 2):"
echo "     python scripts/run_manual.py --flow amazon-test"
echo ""
echo "  4. Prefect UI 확인:"
echo "     http://localhost:4200"
echo ""
echo "  5. 데이터 추출 (수집 후):"
echo "     python scripts/export_data.py"
echo ""
echo "자세한 가이드: TEAMGUIDE.md 참조"
echo "========================================="