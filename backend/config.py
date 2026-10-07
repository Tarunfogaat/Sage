from pathlib import Path

from dotenv import load_dotenv


PROJECT_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_project_environment() -> None:
    load_dotenv(PROJECT_ENV_FILE, override=True)
