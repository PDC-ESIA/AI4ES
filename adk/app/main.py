import logging
from pathlib import Path

from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = get_fast_api_app(
    agents_dir="agents",
    web=True,
    allow_origins=["*"],
)
