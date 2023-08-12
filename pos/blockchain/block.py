from dataclasses import dataclass
from io import BytesIO
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

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
        # decode signature (256 bytes because of 2048 key length)
        # https://crypto.stackexchange.com/questions/95878/does-the-signature-length-of-rs256-depend-on-the-size-of-the-rsa-key-used-for-si
        signature = read_bytes(s, 256)
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

    def verify(self, public_key: RSAPublicKey) -> bool:
        all_data = bytearray(self.encode())
        data = b''.join([bytes(all_data[:56]) + bytes(all_data[312:])])
        try:
            public_key.verify(
                self.signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except InvalidSignature:
            return False
        return True

    def __dict__(self):
        return {
            'version': self.version,
            'timestamp': self.timestamp,
            'prev_hash': self.prev_hash,
            'validator': self.validator,
            'signature': self.signature,
            'transactions': [transaction.__dict__ for transaction in self.transactions]
        }


@dataclass
class BlockProposition:
    version: int
    timestamp: int
    prev_hash: bytes | None
    validator: UUID | None
    transactions: list[Transaction]

    def encode(self) -> bytes:
        if not self.prev_hash or not self.validator:
            raise Exception("Cannot encode without prev_hash and validator")
        out = []
        out += [encode_int(self.version, 4)]
        out += [encode_int(self.timestamp, 4)]
        out += [self.prev_hash]
        out += [self.validator.bytes_le]
        out += [encode_int(len(self.transactions), 4)]
        out += [b''.join([tx.encode() for tx in self.transactions])]
        return b''.join(out)

    def sign(self, prev_hash: bytes, validator: UUID, private_key: RSAPrivateKey) -> Block:
        self.prev_hash = prev_hash
        self.validator = validator
        signature = private_key.sign(
            self.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return Block(
            self.version,
            self.timestamp,
            self.prev_hash,
            self.validator,
            signature,
            self.transactions
        )
