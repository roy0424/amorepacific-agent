#!/usr/bin/env python3
"""
팀 회의용 리포트 생성 스크립트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.reporters.team_report_generator import TeamReportGenerator
from loguru import logger

if __name__ == "__main__":
    print()
    print("=" * 80)
    print("  📊 Laneige 팀 회의 리포트 생성")
    print("=" * 80)
    print()
    print("수집된 모든 데이터를 Excel 형태로 정리합니다:")
    print("  • Amazon 랭킹 데이터")
    print("  • Laneige 제품 현황")
    print("  • 소셜 미디어 데이터")
    print("  • 이벤트 발생 현황")
    print("  • 시스템 설정")
    print()
    print("⏳ 리포트 생성 중...")
    print()

    try:
        generator = TeamReportGenerator()
        filepath = generator.generate_full_report()

        print()
        print("=" * 80)
        print("  ✅ 리포트 생성 완료!")
        print("=" * 80)
        print()
        print(f"📄 파일 위치:")
        print(f"   {filepath}")
        print()
        print("📊 포함된 시트:")
        print("   1. 📊 요약 - 전체 현황 대시보드")
        print("   2. 🎯 Laneige 제품 - 제품별 상세 현황")
        print("   3. 📈 랭킹 추이 - 최근 7일 시계열 차트")
        print("   4. 📂 카테고리별 - 카테고리별 통계")
        print("   5. 📱 소셜미디어 - YouTube/TikTok 인기 컨텐츠")
        print("   6. 🎯 이벤트 - 감지된 이벤트 목록")
        print("   7. ⚙️ 시스템 설정 - 현재 설정값")
        print("   8. 📋 Raw Data - 최근 1000개 원본 데이터")
        print()
        print("💡 사용법:")
        print("   • Excel에서 파일을 열어보세요")
        print("   • 각 시트를 탭으로 전환하며 확인")
        print("   • 필터, 정렬, 차트 추가 가능")
        print()
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("  ❌ 오류 발생")
        print("=" * 80)
        print()
        print(f"오류 내용: {e}")
        print()
        import traceback
        traceback.print_exc()
