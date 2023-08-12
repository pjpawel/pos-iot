import logging
import os
import json
import socket
from base64 import b64encode
from hashlib import sha256
from io import BytesIO
from uuid import uuid4

import requests

from .block import Block, BlockCandidate
from pos.network.peer import Handler
from .transaction import Tx
from .utils import is_file, is_dir
from .node import Node, SelfNode


def encode_chain(blocks: list[Block]) -> bytes:
    return b''.join([block.encode() for block in blocks])


def decode_chain(byt: bytes) -> list[Block]:
    b = BytesIO(byt)
    end = len(byt)
    blocks = []
    while True:
        blocks.append(Block.decode(b))
        if end - b.tell() == 0:
            break
    return blocks


class Blockchain:
    BLOCKCHAIN_PATH = 'blockchain'
    NODES_PATH = 'nodes'

    storage_dir: str
    chain: list[Block]
    nodes: list[Node]
    candidate: BlockCandidate | None = None

    def __init__(self):
        self.storage_dir = os.getenv('STORAGE_DIR')
        self.chain = []
        self.nodes = []

    def add_new_transaction(self, tx: Tx):
        if not self.candidate:
            self.candidate = BlockCandidate.create_new([])
        tx.validate(self.nodes)
        self.candidate.transactions.append(tx)

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

    def create_first_block(self, self_node: SelfNode) -> None:
        block = BlockCandidate.create_new([])
        self.chain.append(block.sign(
            sha256(b'0000000000').digest(),
            self_node.identifier,
            self_node.private_key
        ))

    def load_from_genesis_node(self, genesis_ip: str) -> None:
        data = {
            "port": 5000,
            "register": True,
            "lastBlock": None
        }
        response = requests.post(f"http://{genesis_ip}:{5000}/genesis/register_node", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}")
        response_json = response.json()
        self.chain = [block.__dict__ for block in response_json["blockchain"]]
        self.nodes = [node.__dict__ for node in response_json["nodes"]]

    def update_from_genesis_node(self, genesis_ip: str) -> None:
        data = {"port": 5000}
        response = requests.post(f"http://{genesis_ip}:{5000}/genesis/register_node", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}")
        response_json = response.json()
        self.chain = [Block.decode() for block in response_json["blockchain"]]
        self.nodes = [node for node in response_json["nodes"]]

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


class PoS:
    blockchain: Blockchain
    self_node: SelfNode

    def __init__(self):
        self.blockchain = Blockchain()

    def load(self) -> None:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        genesis_ip = os.getenv("GENESIS_NODE")

        if ip == genesis_ip:
            name = "genesis"
        else:
            name = "node"
        print(f"=== Running as {name} ===")

        if self.blockchain.has_storage_files():
            print("Blockchain loading from storage")
            self.blockchain.load_from_storage()
        elif ip != genesis_ip:
            print("Blockchain loading from genesis")
            self.blockchain.load_from_genesis_node(genesis_ip)
            # Get info from genesis
            response = requests.get(f"http::/{genesis_ip}:5000/info")
            if response.status_code != 200:
                raise Exception(f"Cannot get info from genesis")
            identifier_hex = response.json().get("identifier")
            self.blockchain.nodes.append(Node(identifier_hex, genesis_ip, 5000))

        self.self_node = SelfNode.load()
        self.blockchain.exclude_self_node(ip)

        if ip == genesis_ip and not self.blockchain.chain:
            self.blockchain.create_first_block(self.self_node)

    def add_transaction(self, data: bytes) -> None:
        b = BytesIO(data)
        tx = Tx.decode(b)
        self.blockchain.add_new_transaction(tx)

    def populate_new_node(self, data: dict) -> None:
        identifier = data.get("identifier")
        host = data.get("host")
        port = int(data.get("port"))
        self.blockchain.nodes.append(Node(bytes.fromhex(identifier), host, port))

    def genesis_register(self, node_ip: str) -> dict:
        identifier = uuid4()
        new_node = Node(identifier, node_ip, 5000)
        data_to_send = {
            "identifier": new_node.identifier.bytes_le.hex(),
            "host": new_node.host,
            "port": new_node.port
        }
        for node in self.blockchain.nodes:
            requests.post(f"http://{node.host}:{node.port}/node/populate-new", data_to_send, timeout=15.0)
        self.blockchain.nodes.append(new_node)
        return data_to_send

    def genesis_update(self, data: dict) -> dict:
        last_block_hash = data.get("lastBlock", None)
        excluded_nodes = data.get("nodeIdentifiers", [])

        blocks_to_show = None
        if last_block_hash is not None:
            blocks_to_show = []
            for block in self.blockchain.chain[::-1]:
                blocks_to_show.append(block)
                if block.prev_hash == last_block_hash:
                    break
            blocks_to_show.reverse()

        nodes_to_show = None
        if excluded_nodes:
            nodes_to_show = []
            for node in self.blockchain.nodes:
                if node.identifier.hex not in excluded_nodes:
                    nodes_to_show.append(node)

        blocks_encoded = encode_chain(blocks_to_show or self.blockchain.chain)
        return {
            "blockchain": b64encode(blocks_encoded).hex(),
            "nodes": [node.__dict__ for node in nodes_to_show or self.blockchain.nodes]
        }
