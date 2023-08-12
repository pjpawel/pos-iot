import os
from dataclasses import dataclass
from uuid import UUID, uuid4
import json

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from .request import get_public_key


@dataclass
class Node:
    identifier: UUID
    host: str
    port: int

    def __init__(self, identifier: bytes | str | UUID, host: str, port: int):
        if isinstance(identifier, bytes):
            self.identifier = UUID(bytes_le=identifier)
        elif isinstance(identifier, str):
            self.identifier = UUID(identifier)
        elif isinstance(identifier, UUID):
            self.identifier = identifier
        else:
            raise Exception("Unknown type of identifier: " + type(identifier))
        self.host = host
        self.port = port

    def get_public_key(self) -> Ed25519PublicKey:
        return Ed25519PublicKey.from_public_bytes(get_public_key(self.host, self.port))

    def get_public_key_str(self) -> str:
        return self.get_public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")


class SelfNode(Node):
    INFO_PATH = 'node.json'

    public_key: RSAPublicKey
    private_key: RSAPrivateKey

    def get_public_key(self) -> RSAPublicKey:
        return self.public_key

    @classmethod
    def load(cls):
        storage = os.getenv('STORAGE_DIR')
        key_path = os.path.join(storage, cls.INFO_PATH)
        if os.path.isfile(key_path):
            with open(key_path) as f:
                keys = json.load(f)
            node = cls(bytes.fromhex(keys.get("identifier")), "localhost", 5000)
            private_key_stream = bytes(keys.get("private"), "utf-8")
            node.private_key = serialization.load_pem_private_key(private_key_stream, password=None)
            public_key_stream = bytes(keys.get("public"), "utf-8")
            node.public_key = serialization.load_pem_public_key(public_key_stream)
        else:
            node = cls(uuid4(), "localhost", 5000)
            node.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            node.public_key = node.private_key.public_key()
            node.dump(storage)
        return node

    def dump(self, storage_dir: str) -> None:
        private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(os.path.join(storage_dir, self.INFO_PATH), "w") as f:
            json.dump({
                "public": public_key_pem.decode("utf-8"),
                "private": private_key_pem.decode("utf-8"),
                "identifier": self.identifier.bytes_le.hex()
            }, f)
