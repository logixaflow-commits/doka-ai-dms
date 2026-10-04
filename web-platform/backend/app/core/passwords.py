"""Password hashing helpers shared by registration and login."""

import hashlib

import bcrypt

HASH_PREFIX = "bcrypt-sha256$"


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    try:
        return password.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Password must be valid Unicode text.") from exc


def _prehash(password: str) -> bytes:
    """Prehash UTF-8 passwords so bcrypt accepts passwords of any length."""
    return hashlib.sha256(_password_bytes(password)).digest()


def hash_password(password: str) -> str:
    """Hash a password using the versioned bcrypt-SHA256 format."""
    return HASH_PREFIX + bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode(
        "utf-8"
    )


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, bool]:
    """Return whether a password matches and whether the hash needs upgrading."""
    if not isinstance(hashed_password, str):
        return False, False
    try:
        if hashed_password.startswith(HASH_PREFIX):
            match = bcrypt.checkpw(
                _prehash(plain_password),
                hashed_password[len(HASH_PREFIX) :].encode("utf-8"),
            )
            return match, False

        password_bytes = _password_bytes(plain_password)
        if len(password_bytes) > 72:
            return False, False
        match = bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
        return match, match
    except (TypeError, ValueError, UnicodeError):
        return False, False
