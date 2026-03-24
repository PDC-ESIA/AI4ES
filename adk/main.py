import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Criar o app ADK primeiro
app: FastAPI = get_fast_api_app(agents_dir="src/agents", web=True, allow_origins=["*"])
