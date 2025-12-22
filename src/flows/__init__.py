"""
Prefect Flows package
"""

from .amazon_flow import amazon_pipeline, amazon_quick_test

__all__ = ["amazon_pipeline", "amazon_quick_test"]
