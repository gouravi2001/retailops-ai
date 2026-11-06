"""Configuration is loaded from environment; local .env is optional."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./retailops.db")
API_KEY = os.getenv("API_KEY", "")
APP_ENV = os.getenv("APP_ENV", "development").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if APP_ENV == "production" and (not API_KEY or len(API_KEY) < 24):
    raise RuntimeError("Production requires a unique API_KEY of at least 24 characters")
