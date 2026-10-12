import re
import random
import string


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def random_suffix(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))