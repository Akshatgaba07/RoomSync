import os, sys
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", str(ROOT / ".env")), extra="ignore")
    env: str = "development"
    mongodb_uri: str = "mongodb://localhost:27017"   # "mongomock://" = in-memory (tests/demo only)
    mongodb_db: str = "roomsync"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60 * 12
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ml_dir: str = str(ROOT / "ml")
    models_dir: str = str(ROOT / "models")
    demo_password: str = "RoomSync-demo-1"
    auto_seed_demo: bool = False   # seed synthetic demo accounts on startup (needed for mongomock://)
    university_admin_key: str = ""  # required to use the university CSV matching endpoints


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.env == "production" and s.jwt_secret == "dev-only-change-me":
        raise RuntimeError("JWT_SECRET must be set in production")
    if s.ml_dir not in sys.path:
        sys.path.insert(0, s.ml_dir)
    return s
