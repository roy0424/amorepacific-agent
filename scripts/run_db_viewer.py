#!/usr/bin/env python3
"""
데이터베이스 뷰어 UI 실행 스크립트
"""
import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
ui_script = project_root / "ui" / "db_viewer.py"

print("=" * 80)
print("  🗂️ Laneige Database Viewer 시작")
print("=" * 80)
print()
print("🌐 URL: http://localhost:8502")
print()
print("⏹️  종료: Ctrl+C")
print("=" * 80)
print()

try:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ui_script),
            "--server.port",
            "8502",
            "--server.headless",
            "true",
        ]
    )
except KeyboardInterrupt:
    print("\n\nDB Viewer를 종료합니다.")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    print("\n설치 확인:")
    print("  pip install streamlit==1.40.2")
