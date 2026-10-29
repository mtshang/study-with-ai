import hashlib
import secrets
import threading
import time
from collections import OrderedDict
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException

password_hasher = PasswordHasher()
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))
COOKIE = "study_session"

def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def verify_password(value: str, encoded: str) -> bool:
    try: return password_hasher.verify(encoded, value)
    except (VerificationError, InvalidHashError): return False

class AuthLimiter:
    """Bounded in-process limiter for the initial single-worker local deployment."""
    def __init__(self):
        self.lock = threading.Lock()
        self.buckets = OrderedDict()

    def check(self, key: str):
        now = time.monotonic()
        with self.lock:
            start, count = self.buckets.get(key, (now, 0))
            if now - start >= 60: start, count = now, 0
            if count >= 20:
                raise HTTPException(429, "操作过于频繁，请稍后再试", headers={"Retry-After": "60"})
            self.buckets[key] = (start, count + 1)
            self.buckets.move_to_end(key)
            if len(self.buckets) > 10000: self.buckets.popitem(last=False)

auth_limiter = AuthLimiter()
