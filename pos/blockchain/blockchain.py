import os
import json
import requests

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from cryptography.hazmat.primitives import serialization
import jsonpickle

from .block import Block
from pos.network.peer import Handler
from .util import is_file, is_dir
from .exception import PublicKeyNotFoundException


class Node:
    host: str
    port: int

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def get_public_key(self) -> RSAPublicKey:
        response = requests.get(f"http://{self.host}:{self.port}/public-key")
        if response.status_code != 200:
            raise PublicKeyNotFoundException(f"Cannot get public key from node: {self.host}:{self.port}")
        return serialization.load_pem_public_key(response.content)  # bytes(response.text, "utf-8")

    def to_json(self):
        return {
            "host": self.host,
            "port": self.port
        }


class SelfNode(Node):
    KEYS = 'keys.json'

    public_key: RSAPublicKey
    private_key: RSAPrivateKey

    def get_public_key(self) -> RSAPublicKey:
        return self.public_key

    @staticmethod
    def load_self():
        storage = os.getenv('STORAGE_DIR')
        node = SelfNode("localhost", 5000)
        key_path = os.path.join(storage, SelfNode.KEYS)
        if is_file(key_path):
            with open(key_path) as f:
                keys = json.load(f)
            private_key_stream = bytes(keys["private"], "utf-8")
            node.private_key = serialization.load_pem_private_key(private_key_stream, password=None)
            public_key_stream = bytes(keys["public"], "utf-8")
            node.public_key = serialization.load_pem_public_key(public_key_stream)
        else:
            node.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            private_key_pem = node.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            node.public_key = node.private_key.public_key()
            public_key_pem = node.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            node.dump(storage, private_key_pem.decode("utf-8"), public_key_pem.decode("utf-8"))
        return node

    def dump(self, storage_dir: str, private_key: str, public_key: str) -> None:
        with open(os.path.join(storage_dir, self.KEYS), "w") as f:
            json.dump({
                "public": public_key,
                "private": private_key
            }, f)


class Blockchain:
    BLOCKCHAIN_PATH = 'blockchain.json'
    NODES_PATH = 'nodes.json'

    storage_dir: str
    chain: list[Block]
    nodes: list[Node]

    def __init__(self):
        self.storage_dir = os.getenv('STORAGE_DIR')
        self.chain = []
        self.nodes = []

    def add_block(self, block: Block) -> None:
        self.chain.append(block)

    def has_storage_files(self) -> bool:
        return is_dir(self.storage_dir) \
            and is_file(os.path.join(self.storage_dir, self.BLOCKCHAIN_PATH)) \
            and is_file(os.path.join(self.storage_dir, self.NODES_PATH))

    def load_from_storage(self) -> None:
        with open(os.path.join(self.storage_dir, self.BLOCKCHAIN_PATH)) as f:
            self.chain = json.load(f)
        with open(os.path.join(self.storage_dir, self.NODES_PATH)) as f:
            self.nodes = json.load(f)

    def dump_to_storage(self) -> None:
        with open(os.path.join(self.storage_dir, self.BLOCKCHAIN_PATH), 'w') as f:
            json.dump(self.chain, f)
        with open(os.path.join(self.storage_dir, self.NODES_PATH), 'w') as f:
            json.dump(self.nodes, f)

    def load_from_genesis_node(self, genesis_ip: str) -> None:
        data = {"port": 5000}
        response = requests.post(f"http://{genesis_ip}:{5000}/genesis/register_node", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}")
        response_json = response.json()
        self.chain = [jsonpickle.decode(block) for block in response_json["blockchain"]]
        self.nodes = [jsonpickle.decode(node) for node in response_json["nodes"]]

    def exclude_self_node(self, self_ip: str):
        for node in self.nodes:
            if node.host == self_ip:
                self.nodes.remove(node)

    def blocks_to_dict(self):
        return [block.__dict__ for block in self.chain]

    def nodes_to_dict(self):
        return [node.__dict__ for node in self.nodes]

    # def __del__(self):
    #     self.dump_to_storage()


class BlockchainHandler(Handler):
    blockchain: Blockchain

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def handle(self, data: str):
        print("=========")
        print("Data received")
        print(data)
        print("=========")
