from pymongo import ASCENDING
from .config import get_settings

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        s = get_settings()
        if s.mongodb_uri.startswith("mongomock"):
            import mongomock
            _client = mongomock.MongoClient()
        else:
            from pymongo import MongoClient
            _client = MongoClient(s.mongodb_uri, serverSelectionTimeoutMS=4000)
        _db = _client[s.mongodb_db]
        _db.users.create_index([("email", ASCENDING)], unique=True)
        _db.feedback.create_index([("user_id", ASCENDING)])
    return _db


def reset_db():
    """Drop cached handle (tests)."""
    global _client, _db
    _client = _db = None
