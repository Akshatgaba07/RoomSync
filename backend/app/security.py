from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from .config import get_settings

ALGO = "HS256"


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode()[:72], h.encode())
    except ValueError:
        return False


def make_token(user_id: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": exp}, s.jwt_secret, algorithm=ALGO)


def decode_token(token: str) -> str | None:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGO]).get("sub")
    except jwt.PyJWTError:
        return None
