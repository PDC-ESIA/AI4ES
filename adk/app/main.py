import logging

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app: FastAPI = get_fast_api_app(
    agents_dir="agents/roles",
    web=True,
    allow_origins=["*"]
)