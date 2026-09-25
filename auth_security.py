"""
NER-SAFE: Authentication & Security Utilities
Production-grade cryptographic routines:
- NIST-approved PBKDF2-HMAC-SHA256 password hashing with unique salt
- Constant-time password verification via hmac.compare_digest
- Password complexity validation
- Cryptographically secure session identifier generation
- In-memory rate limiting / throttling for authentication attempts
"""

import os
import hashlib
import hmac
import secrets
import re
import time
from typing import Tuple, Dict

# Salt length in bytes
SALT_BYTES = 16
# PBKDF2 iterations
PBKDF2_ITERATIONS = 100_000

def hash_password(plaintext: str) -> str:
    """
    Hashes a plaintext password using PBKDF2-HMAC-SHA256 with a unique 16-byte random salt.
    Format: pbkdf2_sha256$100000$<salt_hex>$<hash_hex>
    """
    if not isinstance(plaintext, str) or not plaintext:
        raise ValueError("Password must be a non-empty string")
    
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        plaintext.encode('utf-8'),
        salt,
        PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"

def verify_password(plaintext: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    if not isinstance(plaintext, str) or not isinstance(stored_hash, str):
        return False
    
    parts = stored_hash.split('$')
    if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
        return False
    
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])
    except (ValueError, TypeError):
        return False
    
    computed_hash = hashlib.pbkdf2_hmac(
        'sha256',
        plaintext.encode('utf-8'),
        salt,
        iterations
    )
    return hmac.compare_digest(computed_hash, expected_hash)

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Enforces production password strength:
    - At least 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one number (0-9)
    - At least one special symbol (!@#$%^&*()_+-=[]{}|;:,.<>?)
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one numerical digit (0-9)."
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)."
    return True, "Password meets strength requirements."

def normalize_email(email: str) -> str:
    """
    Normalizes email address by trimming whitespace and converting to lowercase.
    """
    if not email or not isinstance(email, str):
        return ""
    return email.strip().lower()

def is_valid_email(email: str) -> bool:
    """
    Validates email format using standard regex pattern.
    """
    email = normalize_email(email)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def generate_session_id() -> str:
    """
    Generates a cryptographically strong 256-bit (32-byte) hex session identifier.
    """
    return secrets.token_hex(32)

class RateLimiter:
    """
    In-memory sliding-window rate limiter to mitigate brute-force and credential-stuffing attacks.
    """
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, list] = {}

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        timestamps = self.attempts.get(key, [])
        # Filter out expired timestamps
        valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
        self.attempts[key] = valid_timestamps
        return len(valid_timestamps) >= self.max_attempts

    def record_attempt(self, key: str):
        now = time.time()
        timestamps = self.attempts.get(key, [])
        timestamps.append(now)
        self.attempts[key] = [t for t in timestamps if now - t < self.window_seconds]

    def reset(self, key: str):
        if key in self.attempts:
            del self.attempts[key]

# Global login rate limiter: 5 failed attempts per 5 minutes per IP/email
login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)
