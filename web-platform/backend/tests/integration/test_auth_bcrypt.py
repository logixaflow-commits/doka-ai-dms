import bcrypt

from app.core.passwords import hash_password, verify_password


def test_register_long_password_and_login():
    password = "Long-Password-" + "x" * 86
    assert len(password) == 100
    stored_hash = hash_password(password)

    assert verify_password(password, stored_hash) == (True, False)


def test_old_bcrypt_hash_still_works_and_rehashes():
    password = "Legacy-Password-123!"
    old_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    valid, needs_rehash = verify_password(password, old_hash)
    assert valid
    assert needs_rehash

    upgraded_hash = hash_password(password)
    assert verify_password(password, upgraded_hash) == (True, False)


def test_wrong_password_rejected():
    stored_hash = hash_password("Correct-Password-123!")

    assert verify_password("Wrong-Password-123!", stored_hash) == (False, False)


def test_short_password_still_works():
    password = "short"
    stored_hash = hash_password(password)

    assert verify_password(password, stored_hash) == (True, False)
    assert verify_password(password + "x", stored_hash) == (False, False)
