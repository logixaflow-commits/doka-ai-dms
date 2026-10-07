"""Password hashing helpers shared by registration and login."""

import hashlib

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

HASH_PREFIX = "bcrypt-sha256$"  # legacy format retained for transparent migration
PASSWORD_HASHER = PasswordHasher()


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    try:
        return password.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Password must be valid Unicode text.") from exc


def _prehash(password: str) -> bytes:
    """Prehash only legacy bcrypt-sha256 passwords during migration."""
    return hashlib.sha256(_password_bytes(password)).digest()


def hash_password(password: str) -> str:
    """Hash new passwords with Argon2id."""
    _password_bytes(password)
    return PASSWORD_HASHER.hash(password)



def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, bool]:
    """Return whether a password matches and whether its hash needs upgrading."""
    if not isinstance(hashed_password, str):
        return False, False
    try:
        if hashed_password.startswith("$argon2"):
            match = PASSWORD_HASHER.verify(hashed_password, plain_password)
            return match, PASSWORD_HASHER.check_needs_rehash(hashed_password)

        if hashed_password.startswith(HASH_PREFIX):
            match = bcrypt.checkpw(
                _prehash(plain_password),
                hashed_password[len(HASH_PREFIX) :].encode("utf-8"),
            )
            return match, match

        password_bytes = _password_bytes(plain_password)
        if len(password_bytes) > 72:
            return False, False
        match = bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
        return match, match
    except (TypeError, ValueError, UnicodeError, VerificationError):
        return False, False
