import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
SCHEDULE_HOURS = os.getenv("SCHEDULE_HOURS", "7,15,18")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "obiady.db"))

# Ensure directory for DB exists
os.makedirs(Path(DATABASE_PATH).parent, exist_ok=True)
