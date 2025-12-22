#!/usr/bin/env python3
"""
원클릭 실행 스크립트 - Prefect 서버 + 자동 스케줄링

이 스크립트 하나만 실행하면:
1. Prefect 서버 시작
2. Flow 자동 배포 (스케줄 설정)
3. 주기적으로 자동 실행 시작
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path
from loguru import logger
import requests

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings


class PrefectManager:
    def __init__(self):
        self.server_process = None
        self.worker_process = None
        self.ui_process = None
        self.db_viewer_process = None

    def ensure_work_pool(self):
        """Prefect work pool/queue 존재 확인 및 생성"""
        pool_name = settings.PREFECT_WORK_POOL_NAME
        queue_name = settings.PREFECT_WORK_QUEUE_NAME
        if not self.wait_for_api_ready():
            return False
        try:
            result = subprocess.run(
                ["prefect", "work-pool", "ls"],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            logger.error("❌ Prefect CLI를 찾을 수 없습니다")
            return False

        if result.returncode != 0:
            logger.error(f"❌ Work pool 조회 실패: {result.stderr.strip()}")
            return False

        if pool_name not in result.stdout:
            logger.info(f"🧩 Work pool 생성: {pool_name}")
            create_result = subprocess.run(
                ["prefect", "work-pool", "create", pool_name, "--type", "process"],
                check=False,
                capture_output=True,
                text=True,
            )
            if create_result.returncode != 0:
                logger.error(f"❌ Work pool 생성 실패: {create_result.stderr.strip()}")
                return False

        queue_result = subprocess.run(
            ["prefect", "work-queue", "ls", "--pool", pool_name],
            check=False,
            capture_output=True,
            text=True,
        )
        if queue_result.returncode != 0:
            logger.error(f"❌ Work queue 조회 실패: {queue_result.stderr.strip()}")
            return False

        if queue_name in queue_result.stdout:
            return True

        logger.info(f"🧩 Work queue 생성: {queue_name} (pool: {pool_name})")
        create_queue_result = subprocess.run(
            ["prefect", "work-queue", "create", queue_name, "--pool", pool_name],
            check=False,
            capture_output=True,
            text=True,
        )
        if create_queue_result.returncode != 0:
            logger.error(f"❌ Work queue 생성 실패: {create_queue_result.stderr.strip()}")
            return False

        return True

    def wait_for_api_ready(self, timeout_seconds: int = 60) -> bool:
        """Prefect API가 준비될 때까지 대기"""
        api_url = os.environ.get("PREFECT_API_URL", "http://localhost:4200/api").rstrip("/")
        health_url = f"{api_url}/health"
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                response = requests.get(health_url, timeout=2)
                if response.ok:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)

        logger.warning(f"⚠️  Prefect API 준비 실패: {health_url}")
        return False

    def start_server(self):
        """Prefect 서버를 백그라운드에서 시작"""
        logger.info("=" * 80)
        logger.info("🚀 Prefect 서버 시작 중...")
        logger.info("=" * 80)

        try:
            # 서버를 백그라운드 프로세스로 시작 (외부 접속 허용)
            self.server_process = subprocess.Popen(
                ["prefect", "server", "start", "--host", "0.0.0.0"],
                text=True
            )

            logger.info("⏳ 서버 초기화 대기 중 (10초)...")
            time.sleep(10)

            # 서버가 실행 중인지 확인
            if self.server_process.poll() is not None:
                logger.error(
                    "❌ Prefect 서버 시작 실패 (exit code: %s)",
                    self.server_process.returncode
                )
                return False

            logger.success("✅ Prefect 서버 시작 완료")
            logger.info("📊 UI: http://localhost:4200")
            return True

        except FileNotFoundError:
            logger.error("❌ Prefect가 설치되어 있지 않습니다")
            logger.info("설치: pip install prefect==3.1.11")
            return False
        except Exception as e:
            logger.error(f"❌ 서버 시작 실패: {e}")
            return False

    def start_worker(self):
        """Worker를 백그라운드에서 시작 (Flow 자동 실행용)"""
        logger.info("\n" + "=" * 80)
        logger.info("⚙️  Worker 시작 중 (Flow 자동 실행용)...")
        logger.info("=" * 80)

        try:
            pool_name = settings.PREFECT_WORK_POOL_NAME
            queue_name = settings.PREFECT_WORK_QUEUE_NAME
            if settings.PREFECT_USE_SERVE:
                deploy_script = project_root / "scripts" / "deploy_flows.py"
                self.worker_process = subprocess.Popen(
                    [sys.executable, str(deploy_script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                self.worker_process = subprocess.Popen(
                    ["prefect", "worker", "start", "--pool", pool_name, "--work-queue", queue_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

            logger.info("⏳ Worker 초기화 대기 중 (5초)...")
            time.sleep(5)

            # Worker가 실행 중인지 확인
            if self.worker_process.poll() is not None:
                logger.error("❌ Worker 시작 실패")
                return False

            logger.success("✅ Worker 시작 완료")
            if settings.PREFECT_USE_SERVE:
                logger.info("🔄 serve()가 스케줄을 등록하고 워커를 실행합니다")
            else:
                logger.info(f"🔄 Flow가 스케줄에 따라 자동 실행됩니다 (pool: {pool_name}, queue: {queue_name})")
            return True

        except Exception as e:
            logger.error(f"❌ Worker 시작 실패: {e}")
            return False

    def deploy_flows(self):
        """Flow 배포 (스케줄 등록)"""
        if settings.PREFECT_USE_SERVE:
            logger.info("serve() 모드에서는 배포를 별도로 실행하지 않습니다")
            return True
        logger.info("\n" + "=" * 80)
        logger.info("📦 Flow 배포 중...")
        logger.info("=" * 80)

        try:
            deploy_script = project_root / "scripts" / "deploy_flows.py"
            result = subprocess.run(
                [sys.executable, str(deploy_script)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error("❌ Flow 배포 실패")
                logger.error(result.stderr.strip())
                return False

            logger.success("✅ Flow 배포 완료")
            return True
        except Exception as e:
            logger.error(f"❌ Flow 배포 실패: {e}")
            return False
    def start_prompt_tester(self):
        """Prompt Tester UI를 백그라운드에서 시작"""
        logger.info("\n" + "=" * 80)
        logger.info("🧪 Prompt Tester UI 시작 중...")
        logger.info("=" * 80)

        try:
            ui_script = project_root / "scripts" / "run_prompt_tester.py"
            self.ui_process = subprocess.Popen(
                [sys.executable, str(ui_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(3)
            if self.ui_process.poll() is not None:
                logger.error("❌ Prompt Tester UI 시작 실패")
                return False

            logger.success("✅ Prompt Tester UI 시작 완료")
            logger.info("🌐 UI: http://localhost:8501")
            return True

        except Exception as e:
            logger.error(f"❌ Prompt Tester UI 시작 실패: {e}")
            return False

    def start_db_viewer(self):
        """Database Viewer UI를 백그라운드에서 시작"""
        logger.info("\n" + "=" * 80)
        logger.info("🗂️ Database Viewer UI 시작 중...")
        logger.info("=" * 80)

        try:
            ui_script = project_root / "scripts" / "run_db_viewer.py"
            self.db_viewer_process = subprocess.Popen(
                [sys.executable, str(ui_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(3)
            if self.db_viewer_process.poll() is not None:
                logger.error("❌ Database Viewer UI 시작 실패")
                return False

            logger.success("✅ Database Viewer UI 시작 완료")
            logger.info("🌐 UI: http://localhost:8502")
            return True

        except Exception as e:
            logger.error(f"❌ Database Viewer UI 시작 실패: {e}")
            return False
    def show_status(self):
        """현재 상태 표시"""
        logger.info("\n" + "=" * 80)
        logger.info("✅ 시스템 시작 완료!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("📊 Prefect UI: http://localhost:4200")
        logger.info("🧪 Prompt Tester UI: http://localhost:8501")
        logger.info("🗂️ Database Viewer UI: http://localhost:8502")
        logger.info("")
        logger.info("⏰ 자동 스케줄:")
        logger.info("   - Amazon 랭킹 수집: 1시간마다")
        logger.info("   - 이벤트 감지 및 분석: 자동")
        logger.info("")
        logger.info("📝 참고:")
        logger.info("   - 소셜미디어 수집: 수동 실행 (scripts/run_social.py)")
        logger.info("")
        logger.info("🔍 UI에서 확인할 수 있는 것:")
        logger.info("   1. Flow Runs: 실행 내역")
        logger.info("   2. Deployments: 스케줄 설정")
        logger.info("   3. Logs: 실시간 로그")
        logger.info("")
        logger.info("📤 데이터 추출:")
        logger.info("   python scripts/export_data.py --format excel")
        logger.info("")
        logger.info("💡 Tip: 수동 실행")
        logger.info("   python scripts/run_manual.py --flow amazon-test")
        logger.info("")
        logger.info("⏹️  종료: Ctrl+C")
        logger.info("=" * 80)

    def stop(self):
        """Prefect 서버 및 Worker 종료"""
        # Worker 종료
        if self.worker_process:
            logger.info("\n⏹️  Worker 종료 중...")
            self.worker_process.terminate()
            try:
                self.worker_process.wait(timeout=5)
                logger.success("✅ Worker 종료 완료")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️  Worker 강제 종료 중...")
                self.worker_process.kill()
                self.worker_process.wait()

        # Prompt Tester UI 종료
        if self.ui_process:
            logger.info("⏹️  Prompt Tester UI 종료 중...")
            self.ui_process.terminate()
            try:
                self.ui_process.wait(timeout=5)
                logger.success("✅ Prompt Tester UI 종료 완료")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️  Prompt Tester UI 강제 종료 중...")
                self.ui_process.kill()
                self.ui_process.wait()

        if self.db_viewer_process:
            logger.info("⏹️  Database Viewer UI 종료 중...")
            self.db_viewer_process.terminate()
            try:
                self.db_viewer_process.wait(timeout=5)
                logger.success("✅ Database Viewer UI 종료 완료")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️  Database Viewer UI 강제 종료 중...")
                self.db_viewer_process.kill()
                self.db_viewer_process.wait()

        # 서버 종료
        if self.server_process:
            logger.info("⏹️  Prefect 서버 종료 중...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                logger.success("✅ Prefect 서버 종료 완료")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️  서버 강제 종료 중...")
                self.server_process.kill()
                self.server_process.wait()

    def run(self):
        """전체 프로세스 실행"""
        try:
            # 1. 서버 시작
            if not self.start_server():
                return False

            # 1.5. Work pool 확인/생성
            if not self.ensure_work_pool():
                logger.warning("⚠️  Work pool 준비 실패 - 스케줄 실행이 지연될 수 있습니다")

            # 2. Worker 시작 (Flow 자동 배포 + 실행)
            if not self.deploy_flows():
                logger.warning("⚠️  Flow 배포 실패 - 스케줄이 등록되지 않았을 수 있습니다")

            # 3. Worker 시작 (Flow 자동 실행)
            if not self.start_worker():
                logger.warning("⚠️  Worker 시작 실패 - 수동으로 Flow를 실행해야 합니다")

            # 3.5 Prompt Tester UI 시작
            if not self.start_prompt_tester():
                logger.warning("⚠️  Prompt Tester UI 시작 실패 - 수동 실행 필요")

            if not self.start_db_viewer():
                logger.warning("⚠️  Database Viewer UI 시작 실패 - 수동 실행 필요")

            # 4. 상태 표시
            self.show_status()

            # 4. 프로세스 모니터링 (Ctrl+C까지 대기)
            logger.info("\n서버가 실행 중입니다... (Ctrl+C로 종료)\n")

            while True:
                # 서버 프로세스 확인
                if self.server_process and self.server_process.poll() is not None:
                    logger.error("❌ Prefect 서버가 예기치 않게 종료되었습니다")
                    break

                # Worker 프로세스 확인
                if self.worker_process and self.worker_process.poll() is not None:
                    logger.warning("⚠️  Worker가 예기치 않게 종료되었습니다")
                    logger.info("Worker를 재시작합니다...")
                    self.start_worker()

                if self.ui_process and self.ui_process.poll() is not None:
                    logger.warning("⚠️  Prompt Tester UI가 예기치 않게 종료되었습니다")
                    logger.info("Prompt Tester UI를 재시작합니다...")
                    self.start_prompt_tester()

                if self.db_viewer_process and self.db_viewer_process.poll() is not None:
                    logger.warning("⚠️  Database Viewer UI가 예기치 않게 종료되었습니다")
                    logger.info("Database Viewer UI를 재시작합니다...")
                    self.start_db_viewer()

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n\n사용자에 의해 종료되었습니다")
        except Exception as e:
            logger.error(f"\n❌ 오류 발생: {e}")
        finally:
            self.stop()


def main():
    """메인 실행 함수"""
    # 로깅 설정
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Prefect 매니저 시작
    manager = PrefectManager()
    manager.run()


if __name__ == "__main__":
    main()
