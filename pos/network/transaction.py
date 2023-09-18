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
        try:
            data = b''.join([bytes(all_data[:24]) + bytes(all_data[88:])])
            self.validate_data()
            node.get_public_key().verify(self.signature, data)
        except InvalidSignature as error:
            logging.error(error)
            logging.error(f"Transaction data: {b64encode(all_data)}, node public key: {node.get_public_key_str()}")
            raise PoSException(f"Transaction not verified by identifier {self.sender.hex}", 400)
        except Exception as e:
            raise PoSException(f"Validation error: {e}", 400)

    def validate_data(self) -> None:
        t = self.data.get("t")
        if not t:
            raise Exception("Missing 'type' (t) of data in transaction")
        if not isinstance(t, str):
            raise Exception("Invalid type of 'type' (t) in transaction. Must be string")
        data = self.data.get("d")
        if not data:
            raise Exception("Missing 'data' (d) in transaction")
        if not isinstance(data, float) and not isinstance(data, int) and not isinstance(data, str):
            raise Exception("Invalid type of 'data' (d) in transaction. Must be int, float or str")
        note = self.data.get("n")
        if note and not isinstance(note, str):
            raise Exception("Invalid type of 'note' (n) in transaction. Must be string")

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

    def has_verification_result(self, node: Node) -> bool:
        return node.identifier in list(self.voting.keys())

    def add_verification_result(self, node: Node, result: bool) -> None:
        if node.identifier in list(self.voting.keys()):
            logging.warning(f"Voting is already saved from node {node.identifier.hex}")
            #logging.info(f"Voting: " + '_'.join([f"{key.hex}-{self.voting[key]}" for key in list(self.voting.keys())]))
            return
        self.voting[node.identifier] = result
        logging.info(f"Successfully added verification result {result} from {node.identifier.hex}")

    def is_voting_positive(self) -> bool:
        results = list(self.voting.values())
        return results.count(True) > (len(results)/2)

    def get_positive_votes(self) -> int:
        return list(self.voting.values()).count(True)

    def is_ready_to_vote(self, n_voters: int) -> bool:
        results = list(self.voting.values())
        n_result = len(results)
        missing = n_voters - n_result
        if missing == 0:
            return True
        n_positives = results.count(True)
        n_negatives = n_result - n_positives
        return abs(n_positives - n_negatives) > missing

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
