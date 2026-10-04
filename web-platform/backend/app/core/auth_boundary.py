"""Claims accepted by the database-backed user authentication boundary."""

from app.core.local_security import is_local_auth_payload


def database_user_id_from_payload(payload: dict) -> int | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("type") != "access" or is_local_auth_payload(payload):
        return None
    subject = payload.get("sub")
    if (
        not isinstance(subject, str)
        or not subject.isascii()
        or not subject.isdecimal()
        or len(subject) > 19
    ):
        return None
    user_id = int(subject)
    return user_id if user_id > 0 else None
