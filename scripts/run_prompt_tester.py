#!/usr/bin/env python3
"""
프롬프트 테스터 UI 실행 스크립트
"""
import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
ui_script = project_root / "ui" / "prompt_tester.py"

print("=" * 80)
print("  🧪 Laneige Prompt Tester 시작")
print("=" * 80)
print()
print("📊 웹 브라우저가 자동으로 열립니다...")
print("🌐 URL: http://localhost:8501")
print()
print("⏹️  종료: Ctrl+C")
print("=" * 80)
print()

try:
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(ui_script),
        "--server.port", "8501",
        "--server.headless", "true"
    ])
except KeyboardInterrupt:
    print("\n\n프롬프트 테스터를 종료합니다.")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    print("\n설치 확인:")
    print("  pip install streamlit==1.40.2")
