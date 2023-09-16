import json
import logging
from base64 import b64encode, b64decode
from dataclasses import dataclass
from io import BytesIO
from uuid import UUID
from time import time

from cryptography.exceptions import InvalidSignature

from .exception import PoSException
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
        signature = read_bytes(s, 64)
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

    def validate(self, node: Node) -> None:
        all_data = self.encode()
        data = b''.join([bytes(all_data[:24]) + bytes(all_data[88:])])

        try:
            node.get_public_key().verify(self.signature, data)
        except InvalidSignature as error:
            logging.error(error)
            logging.error(f"Transaction data: {b64encode(all_data)}, node public key: {node.get_public_key_str()}")
            raise PoSException(f"Transaction not verified by identifier {self.sender.hex}", 400)

    def to_dict(self):
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "sender": self.sender.hex,
            "data": self.data
        }

    def __str__(self):
        return b64encode(self.encode()).hex()

    @classmethod
    def from_str(cls, data: str):
        return cls.decode(BytesIO(b64decode(bytes.fromhex(data))))


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
        out += [encode_int(self.version, 4)]
        out += [encode_int(self.timestamp, 4)]
        out += [self.sender.bytes_le]
        data_encoded = encode_str(json.dumps(self.data))
        out += [encode_int(len(data_encoded), 4)]
        out += [data_encoded]
        return b''.join(out)

    def sign(self, self_node: SelfNode) -> Tx:
        self.sender = self_node.identifier
        signature = self_node.private_key.sign(self.encode())
        return Tx(self.version, self.timestamp, self.sender, signature, self.data)


@dataclass
class TxToVerify:
    tx: Tx
    node: Node
    voting: dict[UUID, bool]
    time: int

    def __init__(self, tx: Tx, node: Node):
        self.tx = tx
        self.node = node
        self.voting = {}
        self.time = int(time())

    def add_verification_result(self, node: Node, result: bool) -> None:
        if node.identifier in list(self.voting.keys()):
            raise Exception(f"Voting is already saved from node {node.identifier}")
        self.voting[node.identifier] = result

    def is_voting_positive(self) -> bool:
        results = list(self.voting.values())
        return results.count(True) > (len(results)/2)

    def __str__(self) -> str:
        return ':'.join([
            str(self.tx).replace(':', '_'),
            str(self.node).replace(':', '_'),
            '_'.join([f"{key.hex}-{self.voting[key]}" for key in list(self.voting.keys())]),
            str(self.time)
        ])

    @classmethod
    def from_str(cls, data: str):
        split = data.split(':')
        node_info = split[1].split('_')
        node = Node.load_from_list(node_info) if node_info[4] == '0' else SelfNode.load_from_list(node_info)
        tx = cls(
            Tx.from_str((split[0].replace('_', ':'))),
            node
        )
        tx.time = int(split[3])
        if split[2] != "":
            for vote in split[2].split('_'):
                vote_split = vote.split('-')
                tx.voting[UUID(vote_split[0])] = bool(vote_split[1])
        return tx
