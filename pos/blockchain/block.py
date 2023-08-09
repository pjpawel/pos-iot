from dataclasses import dataclass
from io import BytesIO
from uuid import UUID

from .transaction import Transaction
from .utils import decode_int, decode_str, encode_int, encode_str, read_bytes


@dataclass
class Block:
    version: int
    timestamp: int
    prev_hash: bytes
    validator: UUID
    signature: bytes
    transactions: list[Transaction]

    @classmethod
    def decode(cls, s: BytesIO):
        """
        Decode Block from bytes
        <version><timestamp><prev_hash><validator><signature><n_transaction><transactions>
        :param s:
        :return:
        """
        # decode version
        version = decode_int(s, 4)
        # decode timestamp (uint32: 32 bits = 4 bytes)
        timestamp = decode_int(s, 4)
        # decode prev_hash (sha256: 256 bits = 32 bytes)
        prev_hash = read_bytes(s, 32)
        # decode validator (uuid: 16 bytes)
        validator = UUID(bytes_le=read_bytes(s, 16))
        # decode signature (sha256: 256 bits = 32 bytes)
        signature = read_bytes(s, 32)
        # decode header n_transaction
        n_transaction = decode_int(s, 4)
        transactions = []
        for n in range(0, n_transaction):
            transactions.append(Transaction.decode(s))
        return cls(version, timestamp, prev_hash, validator, signature, transactions)

    def encode(self) -> bytes:
        out = []
        out += [encode_int(self.version, 4)]
        out += [encode_int(self.timestamp, 4)]
        out += [self.prev_hash]
        out += [self.validator.bytes_le]
        out += [self.signature]
        out += [encode_int(len(self.transactions), 4)]
        out += [b''.join([tx.encode() for tx in self.transactions])]
        return b''.join(out)

    def __dict__(self):
        return {
            'version': self.version,
            'timestamp': self.timestamp,
            'prev_hash': self.prev_hash,
            'validator': self.validator,
            'signature': self.signature,
            'transactions': [transaction.__dict__ for transaction in self.transactions]
        }
