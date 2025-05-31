import os
from io import BytesIO
from typing import Literal


def is_file(path: str) -> bool:
    return os.path.isfile(path)


def is_dir(path: str) -> bool:
    return os.path.isdir(path)


def decode_int(
    io: BytesIO, n_bytes: int, encoding: Literal["big", "little"] = "little"
) -> int:
    return int.from_bytes(io.read(n_bytes), encoding)


def encode_int(
    i: int, n_bytes: int, encoding: Literal["big", "little"] = "little"
) -> bytes:
    return i.to_bytes(n_bytes, encoding)


def decode_str(io: BytesIO, n_bytes: int) -> str:
    return io.read(n_bytes).decode("utf-8")


def encode_str(s: str, n_bytes: int = None) -> bytes:
    b = s.encode("utf-8")
    if n_bytes is None:
        return b
    if n_bytes != len(b):
        raise Exception(
            f"Error while encoding string {s}, number of bytes {len(b)}, "
            f"but declared number of bytes {n_bytes}"
        )
    return b


def read_bytes(io: BytesIO, n_bytes: int):
    return io.read(n_bytes)
