@echo off
REM Laneige Ranking Tracker - 원클릭 설치 스크립트 (Windows)
REM 팀원들이 쉽게 Prefect 환경을 구축할 수 있도록 돕는 스크립트

echo =========================================
echo Laneige Ranking Tracker 설치 시작
echo =========================================
echo.

REM 1. Python 버전 체크
echo 📌 Step 1/6: Python 버전 확인...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo    ❌ Python이 설치되어 있지 않습니다!
    echo    Python 3.9 이상을 설치하세요: https://python.org
    pause
    exit /b 1
)
echo    ✓ Python 감지됨
echo.

REM 2. 가상환경 생성
echo 📌 Step 2/6: 가상환경 생성...
if exist ".venv" (
    echo    ⚠️  가상환경이 이미 존재합니다. 재사용합니다.
) else (
    python -m venv .venv
    echo    ✓ 가상환경 생성 완료
)
echo.

REM 3. 가상환경 활성화
echo 📌 Step 3/6: 가상환경 활성화...
call .venv\Scripts\activate.bat
echo    ✓ 가상환경 활성화됨
echo.

REM 4. 의존성 설치
echo 📌 Step 4/6: 패키지 설치 중...
echo    (약 2-3분 소요됩니다)
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
echo    ✓ 패키지 설치 완료
echo.

REM 5. Playwright 설치
echo 📌 Step 5/6: Playwright 브라우저 설치...
playwright install chromium
echo    ✓ Playwright 설치 완료
echo.

REM 6. 환경 변수 설정
echo 📌 Step 6/6: 환경 변수 설정...
if not exist ".env" (
    copy .env.example .env
    echo    ✓ .env 파일 생성됨
    echo    ⚠️  .env 파일을 열어서 필요한 API 키를 입력하세요:
    echo       - YOUTUBE_API_KEY (선택)
    echo       - APIFY_API_TOKEN (선택)
    echo       - OPENAI_API_KEY (선택)
) else (
    echo    ✓ .env 파일이 이미 존재합니다
)
echo.

REM 7. 데이터베이스 초기화
echo =========================================
echo 📊 데이터베이스 초기화
echo =========================================
set /p init_db="데이터베이스를 초기화하시겠습니까? (y/n): "
if /i "%init_db%"=="y" (
    python scripts\init_db.py
    echo    ✓ 데이터베이스 초기화 완료
) else (
    echo    ⏭️  데이터베이스 초기화 건너뜀
    echo    (나중에 'python scripts\init_db.py' 실행)
)
echo.

REM 8. 설치 완료
echo =========================================
echo ✅ 설치 완료!
echo =========================================
echo.
echo 다음 명령어로 시작하세요:
echo.
echo   1. 가상환경 활성화 (터미널을 새로 열었을 때):
echo      .venv\Scripts\activate.bat
echo.
echo   2. Prefect 서버 시작 (터미널 1):
echo      python scripts\start_prefect.py
echo.
echo   3. 데이터 수집 실행 (터미널 2):
echo      python scripts\run_manual.py --flow amazon-test
echo.
echo   4. Prefect UI 확인:
echo      http://localhost:4200
echo.
echo   5. 데이터 추출 (수집 후):
echo      python scripts\export_data.py
echo.
echo 자세한 가이드: TEAMGUIDE.md 참조
echo =========================================
pause