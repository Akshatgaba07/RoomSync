from fastapi import APIRouter, HTTPException
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone
from ..db import get_db
from ..schemas import SignupIn, LoginIn, TokenOut
from ..security import hash_password, verify_password, make_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=201)
def signup(body: SignupIn):
    doc = {"email": body.email.lower(), "name": body.name, "password_hash": hash_password(body.password),
           "created_at": datetime.now(timezone.utc), "profile": {"answers": {}, "dealbreakers": [], "priorities": []},
           "profile_complete": False, "is_synthetic": False}
    try:
        res = get_db().users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "An account with this email already exists")
    return TokenOut(access_token=make_token(str(res.inserted_id)))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    u = get_db().users.find_one({"email": body.email.lower()})
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    return TokenOut(access_token=make_token(str(u["_id"])))
