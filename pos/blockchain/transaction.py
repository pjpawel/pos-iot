import json
import logging
from dataclasses import dataclass
from io import BytesIO
from uuid import UUID
from time import time

from cryptography.exceptions import InvalidSignature

from .node import SelfNode, Node
from .utils import decode_int, decode_str, encode_int, encode_str, read_bytes


@dataclass
class Tx:
    version: int
    timestamp: int
    sender: UUID
    signature: bytes
    data: dict

    @classmethod
    def decode(cls, s: BytesIO):
        """
        Decode Tx from bytes
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
        # decode signature (Ed25519: 64 bytes)
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

    def validate(self, node: Node) -> bool:
        all_data = self.encode()
        data = b''.join([bytes(all_data[:24]) + bytes(all_data[56:])])

        try:
            node.get_public_key().verify(self.signature, data)
        except InvalidSignature:
            logging.warning(f"Transaction not verified found with identifier {self.sender.hex}")
            return False

        return self._validate_data()

    def _validate_data(self) -> bool:
        return True


class TxCandidate:
    _DEFAULT_VERSION = 1

    version: int
    timestamp: int
    data: dict
    sender: UUID | None = None

    def __init__(self, data: str | dict):
        if isinstance(data, str):
            data = json.loads(data)
        self.version = self._DEFAULT_VERSION
        self.timestamp = int(time())
        self.data = data

    def encode(self):
        if not self.sender:
            raise Exception("Cannot encode without sender")
        out = []
        out += [self.sender.bytes_le]
        out += [encode_int(self.version, 4)]
        out += [encode_int(self.timestamp, 4)]
        data_encoded = encode_str(json.dumps(self.data))
        out += [encode_int(len(data_encoded), 4)]
        out += [data_encoded]
        return b''.join(out)

    def sign(self, self_node: SelfNode) -> Tx:
        self.sender = self_node.identifier
        signature = self_node.private_key.sign(self.encode())
        return Tx(self.version, self.timestamp, self.sender, signature, self.data)


class TransactionService:
    pass
