"""
Deploy Prefect flows with schedules

This script registers all flows with Prefect and sets up their schedules.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import timedelta
import asyncio
import inspect
import os
import subprocess
import time
from loguru import logger
from prefect import serve
import requests

from src.flows.amazon_flow import amazon_pipeline
from config.settings import settings


def wait_for_api_ready(timeout_seconds: int = 90) -> bool:
    """Wait for Prefect API to become healthy."""
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

    logger.warning(f"Prefect API not ready after {timeout_seconds}s: {health_url}")
    return False


def ensure_work_pool(pool_name: str, queue_name: str) -> None:
    """Ensure the Prefect work pool and queue exist for scheduled deployments."""
    if not wait_for_api_ready():
        raise RuntimeError("Prefect API not ready; cannot create work pool.")

    try:
        result = subprocess.run(
            ["prefect", "work-pool", "ls"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Prefect CLI not found in PATH") from exc

    if result.returncode != 0:
        raise RuntimeError(
            "Failed to list work pools: "
            f"stdout={result.stdout.strip()} stderr={result.stderr.strip()}"
        )

    pool_exists = pool_name in result.stdout
    if not pool_exists:
        logger.info(f"Creating work pool: {pool_name}")
        create_result = subprocess.run(
            ["prefect", "work-pool", "create", pool_name, "--type", "process"],
            check=False,
            capture_output=True,
            text=True,
        )
        if create_result.returncode != 0:
            if "already exists" in create_result.stdout.lower():
                pool_exists = True
            else:
                raise RuntimeError(
                    "Failed to create work pool: "
                    f"stdout={create_result.stdout.strip()} stderr={create_result.stderr.strip()}"
                )
        else:
            pool_exists = True

    queue_result = subprocess.run(
        ["prefect", "work-queue", "ls", "--pool", pool_name],
        check=False,
        capture_output=True,
        text=True,
    )
    if queue_result.returncode != 0:
        raise RuntimeError(
            "Failed to list work queues: "
            f"stdout={queue_result.stdout.strip()} stderr={queue_result.stderr.strip()}"
        )

    if queue_name in queue_result.stdout:
        return

    logger.info(f"Creating work queue: {queue_name} (pool: {pool_name})")
    create_queue_result = subprocess.run(
        ["prefect", "work-queue", "create", queue_name, "--pool", pool_name],
        check=False,
        capture_output=True,
        text=True,
    )
    if create_queue_result.returncode != 0:
        raise RuntimeError(
            "Failed to create work queue: "
            f"stdout={create_queue_result.stdout.strip()} stderr={create_queue_result.stderr.strip()}"
        )


def deploy_all_flows():
    """Deploy all flows with their schedules."""
    logger.info("=" * 80)
    logger.info("Deploying Prefect Flows")
    logger.info("=" * 80)

    try:
        ensure_work_pool(settings.PREFECT_WORK_POOL_NAME, settings.PREFECT_WORK_QUEUE_NAME)

        logger.info(f"Deploying Amazon pipeline (every {settings.AMAZON_SCRAPE_INTERVAL_HOURS} hours)...")

        if settings.PREFECT_USE_SERVE:
            logger.info("Starting serve() to register deployment and run worker...")
            serve(
                amazon_pipeline.to_deployment(
                    name="amazon-hourly",
                    interval=timedelta(hours=settings.AMAZON_SCRAPE_INTERVAL_HOURS),
                    work_pool_name=settings.PREFECT_WORK_POOL_NAME,
                    work_queue_name=settings.PREFECT_WORK_QUEUE_NAME,
                    tags=["production", "amazon", "scraping"],
                )
            )
        else:
            flow_for_deploy = amazon_pipeline.from_source(
                source=str(project_root),
                entrypoint="src/flows/amazon_flow.py:amazon_pipeline",
            )
            deployment_result = flow_for_deploy.deploy(
                name="amazon-hourly",
                interval=timedelta(hours=settings.AMAZON_SCRAPE_INTERVAL_HOURS),
                work_pool_name=settings.PREFECT_WORK_POOL_NAME,
                work_queue_name=settings.PREFECT_WORK_QUEUE_NAME,
                tags=["production", "amazon", "scraping"],
            )

            if inspect.isawaitable(deployment_result):
                deployment_result = asyncio.run(deployment_result)

            logger.success(f"Deployment complete: {deployment_result}")

    except Exception as e:
        logger.error(f"Error deploying flows: {e}")
        raise


def main():
    """Main entry point"""
    logger.info("Starting flow deployment...")

    try:
        deploy_all_flows()
    except KeyboardInterrupt:
        logger.info("\nDeployment stopped by user")
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise


if __name__ == "__main__":
    main()
