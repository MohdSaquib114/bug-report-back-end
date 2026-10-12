import base64
import hashlib
import hmac
import os
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS
    )
    return "{0}${1}${2}${3}".format(
        _ALGORITHM,
        _ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, hashed: str) -> bool:
    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = hashed.split("$")
        if algorithm != _ALGORITHM:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations_raw)
        )
        return hmac.compare_digest(computed, expected)
    except (ValueError, TypeError):
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)