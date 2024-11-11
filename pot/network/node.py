import os
import socket
from dataclasses import dataclass
from uuid import UUID, uuid4
import json
from enum import StrEnum, auto

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives import serialization

from .request import Request


class NodeType(StrEnum):
    SENSOR = auto()
    VALIDATOR = auto()


@dataclass
class Node:
    identifier: UUID
    type: NodeType
    host: str
    port: int

    def __init__(
        self,
        identifier: bytes | str | UUID,
        host: str,
        port: int,
        n_type: NodeType | None | str = None,
    ):
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
        if n_type is None:
            n_type = NodeType.SENSOR
        if isinstance(n_type, str):
            n_type = getattr(NodeType, n_type.upper())
        self.type = n_type

    def set_type(self, n_type: NodeType):
        self.type = n_type

    def get_public_key(self) -> Ed25519PublicKey:
        return serialization.load_pem_public_key(
            Request.get_public_key(self.host, self.port)
        )

    def get_public_key_str(self) -> str:
        return (
            self.get_public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

    @classmethod
    def load_from_dict(cls, data: dict):
        return cls(UUID(data.get("identifier")), data.get("host"), data.get("port"))

    @classmethod
    def load_from_list(cls, data: list):
        return cls(data[0], data[1], int(data[2]), NodeType.SENSOR)

    def to_list(self) -> list[str]:
        return [self.identifier.hex, self.host, str(self.port)]

    def __str__(self) -> str:
        return ":".join(self.to_list())

    @property
    def __dict__(self) -> dict:
        return {
            "identifier": self.identifier.hex,
            "type": self.type.name,
            "host": self.host,
            "port": self.port,
        }


class SelfNodeInfo:
    INFO_PATH = "self_node.json"

    identifier: UUID
    public_key: Ed25519PublicKey
    private_key: Ed25519PrivateKey

    def __init__(self):
        storage = os.getenv("STORAGE_DIR")
        key_path = os.path.join(storage, self.INFO_PATH)
        if os.path.isfile(key_path):
            with open(key_path) as f:
                keys = json.load(f)
            self.identifier = UUID(bytes_le=bytes.fromhex(keys.get("identifier")))
            private_key_stream = bytes(keys.get("private"), "utf-8")
            self.private_key = serialization.load_pem_private_key(
                private_key_stream, password=None
            )
            public_key_stream = bytes(keys.get("public"), "utf-8")
            self.public_key = serialization.load_pem_public_key(public_key_stream)
        else:
            self.identifier = uuid4()
            self.private_key = Ed25519PrivateKey.generate()
            self.public_key = self.private_key.public_key()
            self.dump(storage)

    def get_node(self) -> Node:
        return Node(
            self.identifier,
            socket.gethostbyname(socket.gethostname()),
            5000,
            os.getenv("NODE_TYPE"),
        )

    def get_public_key(self) -> Ed25519PublicKey:
        return self.public_key

    def get_public_key_str(self):
        return (
            self.get_public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

    def dump(self, storage_dir: str) -> None:
        private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with open(os.path.join(storage_dir, self.INFO_PATH), "w") as f:
            json.dump(
                {
                    "public": public_key_pem.decode("utf-8"),
                    "private": private_key_pem.decode("utf-8"),
                    "identifier": self.identifier.bytes_le.hex(),
                },
                f,
            )


class SelfNode(Node):
    public_key: Ed25519PublicKey
    private_key: Ed25519PrivateKey

    def __init__(self, node: Node, self_node_info: SelfNodeInfo):
        super().__init__(node.identifier, node.host, node.port, node.type)
        self.public_key = self_node_info.public_key
        self.private_key = self_node_info.private_key

    def get_public_key(self) -> Ed25519PublicKey:
        return self.public_key

    def get_node(self) -> Node:
        return Node(self.identifier, self.host, self.port, self.type)
