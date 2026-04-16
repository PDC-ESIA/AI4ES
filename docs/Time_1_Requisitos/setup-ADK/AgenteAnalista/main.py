import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

from dotenv import load_dotenv
load_dotenv()

from google.adk.cli.fast_api import get_fast_api_app
import uvicorn

app = get_fast_api_app(agents_dir=os.path.join(ROOT_DIR, "agents"), web=True)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
