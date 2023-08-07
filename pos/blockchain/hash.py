from hashlib import sha256


def hash(timestamp: int, prev_hash: str, data: str) -> str:
    return sha256(str(timestamp)+prev_hash+data).hexdigest()
