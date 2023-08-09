import json
from dataclasses import dataclass
from io import BytesIO
from uuid import UUID

from pos.blockchain.utils import decode_int, decode_str, encode_int, encode_str, read_bytes


@dataclass
class Transaction:
    version: int
    timestamp: int
    sender: UUID
    signature: bytes
    data: dict

    @classmethod
    def decode(cls, s: BytesIO):
        """
        Decode Transaction from bytes
        <version><timestamp(unix)><sender(uuid)><signature><data_length><data>
        :param s:
        :return:
        """
        # decode version
        version = decode_int(s, 4)
        # decode timestamp (uint32: 32 bits = 4 bytes)
        timestamp = decode_int(s, 4)
        # decode sender identifier (uuid: 16 bytes)
        sender = UUID(bytes_le=read_bytes(s, 16))
        # decode signature (sha256: 256 bits = 32 bytes)
        signature = read_bytes(s, 32)
        # decode header data_length
        data_length = decode_int(s, 4)
        data_str = decode_str(s, data_length)
        data = json.loads(data_str)
        return cls(version, timestamp, sender, signature, data)

    def encode(self) -> bytes:
        out = []
        out += [encode_int(self.version, 4)]
        out += [encode_int(self.timestamp, 4)]
        out += [self.sender.bytes_le]
        out += [self.signature]
        data_encoded = encode_str(json.dumps(self.data))
        out += [encode_int(len(data_encoded), 4)]
        out += [data_encoded]
        return b''.join(out)


class TransactionService:
    pass
