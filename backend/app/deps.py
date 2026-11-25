from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .db import get_db
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(404, "Not found")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not cred:
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    uid = decode_token(cred.credentials)
    user = get_db().users.find_one({"_id": oid(uid)}) if uid else None
    if not user:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    return user
