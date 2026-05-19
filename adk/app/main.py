import logging

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from dotenv import load_dotenv
load_dotenv()

app: FastAPI = get_fast_api_app(
    agents_dir="design_agents/roles",
    web=True,
    allow_origins=["*"]
)