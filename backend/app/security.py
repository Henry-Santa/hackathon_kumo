from __future__ import annotations

import bcrypt
import time
import jwt
from typing import Optional
from .config import settings


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def issue_jwt(user_id: str, email: str, ttl_seconds: int = 60 * 60 * 24 * 7) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "iss": settings.jwt_iss,
        "aud": settings.jwt_aud,
        "iat": now,
        "nbf": now,
        "exp": now + ttl_seconds,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_aud,
            issuer=settings.jwt_iss,
        )
    except Exception:
        return None


