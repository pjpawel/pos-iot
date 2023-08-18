import logging
import os
import json
import socket
from base64 import b64encode, b64decode
from hashlib import sha256
from io import BytesIO
from typing import BinaryIO
from uuid import uuid4, UUID
from sys import getsizeof

import requests

from .block import Block, BlockCandidate
from pos.network.peer import Handler
from .transaction import Tx, TxToVerify
from .utils import is_file, is_dir
from .node import Node, SelfNode, NodeType
from .request import get_info, send_populate_verification_result
from .exception import PoSException


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
    blocks: list[Block]
    candidate: BlockCandidate | None = None

    def __init__(self):
        self.blocks = []

    def add_new_transaction(self, tx: Tx, node: Node):
        if not self.candidate:
            self.candidate = BlockCandidate.create_new([])
        self.candidate.transactions.append(tx)

    def create_first_block(self, self_node: SelfNode) -> None:
        block = BlockCandidate.create_new([])
        self.blocks.append(block.sign(
            sha256(b'0000000000').digest(),
            self_node.identifier,
            self_node.private_key
        ))

    def load_from_file(self, f: BinaryIO) -> None:
        self.blocks = decode_chain(f.read(getsizeof(f)))

    def load_from_bytes(self, b: bytes) -> None:
        self.blocks = decode_chain(b)

    def blocks_to_dict(self):
        return [block.__dict__ for block in self.blocks]


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
    BLOCKCHAIN_PATH = 'blockchain'
    NODES_PATH = 'nodes'
    VALIDATORS_PATH = 'validators'

    _storage_dir: str
    blockchain: Blockchain
    self_node: SelfNode
    tx_to_verified: dict[UUID, TxToVerify] = {}
    nodes: list[Node] = []
    validators: list[Node] = []

    def __init__(self):
        self._storage_dir = os.getenv("STORAGE_DIR")
        self.blockchain = Blockchain()
        self.self_node = SelfNode.load(os.getenv("NODE_TYPE"))

    def load(self) -> None:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        genesis_ip = os.getenv("GENESIS_NODE")

        if ip == genesis_ip:
            name = "genesis"
        else:
            name = "node"
        print(f"=== Running as {name} ===")

        if self._has_storage_files():
            print("Blockchain loading from storage")
            # Load from storage
            self._load_from_storage()
        elif ip != genesis_ip:
            print("Blockchain loading from genesis")
            self.load_from_validator_node(genesis_ip)
            identifier_hex = get_info(genesis_ip, 5000).get("identifier")
            self.nodes.append(Node(identifier_hex, genesis_ip, 5000))

        self._exclude_self_node(ip)

        if ip == genesis_ip and not self.blockchain.blocks:
            self.blockchain.create_first_block(self.self_node)

    def nodes_to_dict(self) -> list[dict]:
        return [node.__dict__ for node in self.validators + self.nodes]

    """
    Internal methods
    """

    def load_from_validator_node(self, genesis_ip: str) -> None:
        data = {
            "port": 5000,
            "register": True,
            "lastBlock": None,
            "type": self.self_node.type.name
        }
        response = requests.post(f"http://{genesis_ip}:{5000}/node/register", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}")
        # TODO: update to robi nie register
        response_json = response.json()
        self.blockchain.load_from_bytes(b64decode(bytes.fromhex(response_json.get("blockchain"))))
        self.nodes = [node.__dict__ for node in response_json.get("nodes")]

    def update_from_validator_node(self, genesis_ip: str) -> None:
        data = {"port": 5000}
        response = requests.post(f"http://{genesis_ip}:{5000}/node/update", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}")
        response_json = response.json()
        self.blockchain.load_from_bytes(b64decode(bytes.fromhex(response_json.get("blockchain"))))
        self.nodes = [node.__dict__ for node in response_json.get("nodes")]

    def send_transaction_verification(self, uuid: UUID, tx_to_verify: TxToVerify, verified: bool, message: str | None = None):
        data_to_send = {
            "identifier": uuid.hex,
            "verified": verified,
            "message": message
        }
        for node in self.validators:
            if node == tx_to_verify.node:
                continue
            try:
                send_populate_verification_result(node.host, node.port, data_to_send)
            except Exception as e:
                logging.error(e)

    def _has_storage_files(self) -> bool:
        return is_dir(self._storage_dir) \
            and is_file(os.path.join(self._storage_dir, self.BLOCKCHAIN_PATH)) \
            and is_file(os.path.join(self._storage_dir, self.NODES_PATH)) \
            and is_file(os.path.join(self._storage_dir, self.VALIDATORS_PATH))

    def _exclude_self_node(self, self_ip: str) -> None:
        for node in self.nodes:
            if node.host == self_ip:
                self.nodes.remove(node)
                return
        for node in self.validators:
            if node.host == self_ip:
                self.validators.remove(node)
                return

    def _load_from_storage(self) -> None:
        with open(os.path.join(self._storage_dir, self.BLOCKCHAIN_PATH), "rb") as f:
            self.blockchain.load_from_file(f)
        with open(os.path.join(self._storage_dir, self.NODES_PATH)) as f:
            self.nodes = json.load(f)
        with open(os.path.join(self._storage_dir, self.VALIDATORS_PATH)) as f:
            self.validators = json.load(f)

    def _dump_to_storage(self) -> None:
        with open(os.path.join(self._storage_dir, self.BLOCKCHAIN_PATH), 'wb') as f:
            f.write(encode_chain(self.blockchain.blocks))
        with open(os.path.join(self._storage_dir, self.NODES_PATH), 'w') as f:
            json.dump(self.nodes, f)
        with open(os.path.join(self._storage_dir, self.VALIDATORS_PATH), 'w') as f:
            json.dump(self.validators, f)

    # def __del__(self):
    #     self._dump_to_storage()

    """
    API methods
    """

    def transaction_new(self, data: bytes, request_addr: str) -> dict:
        self._validate_if_i_am_validator()

        b = BytesIO(data)
        tx = Tx.decode(b)
        tx_node = None
        for node in self.nodes + self.validators:
            if node.identifier == tx.sender:
                tx_node = node
                break
        if not tx_node:
            raise Exception(f"Node not found with identifier {tx.sender.hex}")
        if tx_node.host != request_addr:
            raise Exception(f"Node hostname ({tx_node.host}) different than remote_addr: ({request_addr})")
        tx.validate(tx_node)
        uuid = uuid4()
        self.tx_to_verified[uuid] = TxToVerify(tx, tx_node)
        return {"id": uuid.hex}

    def transaction_populate(self, data: bytes, identifier: str):
        uuid = UUID(identifier)
        tx = Tx.decode(BytesIO(data))

        tx_node = None
        for node in self.nodes + self.validators:
            if node.identifier == tx.sender:
                tx_node = node
                break

        if not tx_node:
            raise Exception(f"Node not found with identifier {tx.sender.hex}")

        tx.validate(tx_node)
        self.tx_to_verified[uuid] = TxToVerify(tx, tx_node)

    def transaction_populate_verify_result(self, verified: bool, identifier: str, remote_addr: str):
        self._validate_request_from_validator(remote_addr)
        node = self._get_node_from_request_addr(remote_addr)
        uuid = UUID(identifier)
        tx_to_verified = self.tx_to_verified.get(uuid)
        tx_to_verified.voting[node] = verified
        if len(self.tx_to_verified) == len(self.validators):
            self.blockchain.add_new_transaction(tx_to_verified.tx, tx_to_verified.node)
            self.tx_to_verified.pop(uuid)

    def populate_new_node(self, data: dict, request_addr: str) -> None:
        self._validate_request_from_validator(request_addr)

        identifier = data.get("identifier")
        host = data.get("host")
        port = int(data.get("port"))
        n_type = getattr(NodeType, data.get("type"))

        # check if node is already register
        for node in self.nodes + self.validators:
            if node.host == host and node.port == port:
                raise Exception(f"Node is already registered with identifier: {node.identifier}")

        new_node = Node(identifier, host, port)
        if n_type == NodeType.VALIDATOR:
            self.validators.append(new_node)
        else:
            self.nodes.append(new_node)

    def node_register(self, node_ip: str, port: int, n_type: NodeType) -> dict | tuple:
        self._validate_if_i_am_validator()

        for node in self.nodes + self.validators:
            if node.host == node_ip and node.port == port:
                return {"error": f"Node is already registered with identifier: {node.identifier}"}, 400

        identifier = uuid4()
        new_node = Node(identifier, node_ip, 5000)
        data_to_send = {
            "identifier": new_node.identifier.bytes_le.hex(),
            "host": new_node.host,
            "port": new_node.port,
            "type": n_type
        }

        # Populate nodes
        for node in self.validators:
            requests.post(f"http://{node.host}:{node.port}/node/populate-new", data_to_send, timeout=15.0)

        if n_type == NodeType.VALIDATOR:
            self.validators.append(new_node)
        else:
            self.nodes.append(new_node)

        return data_to_send

    def node_update(self, data: dict) -> dict | tuple:
        self._validate_if_i_am_validator()

        last_block_hash = data.get("lastBlock", None)
        excluded_nodes = data.get("nodeIdentifiers", [])

        blocks_to_show = None
        if last_block_hash is not None:
            blocks_to_show = []
            for block in self.blockchain.blocks[::-1]:
                blocks_to_show.append(block)
                if block.prev_hash == last_block_hash:
                    break
            blocks_to_show.reverse()

        nodes_to_show = None
        if excluded_nodes:
            nodes_to_show = []
            for node in self.nodes + self.validators:
                if node.identifier.hex not in excluded_nodes:
                    nodes_to_show.append(node)

        blocks_encoded = encode_chain(blocks_to_show or self.blockchain.blocks)
        return {
            "blockchain": b64encode(blocks_encoded).hex(),
            "nodes": [node.__dict__ for node in nodes_to_show or (self.nodes + self.validators)]
        }

    """
    Internal API methods
    """

    def _validate_if_i_am_validator(self) -> None:
        if not self.self_node.type == NodeType.VALIDATOR:
            raise PoSException({"error": "I am not validator"}, 400)

    def _validate_request_from_validator(self, request_addr: str) -> None:
        validator = False
        for node in self.validators:
            if node.host == request_addr:
                validator = True
        if not validator:
            raise PoSException({"error": "Request came from node which is not validator"}, 400)

    def _get_node_from_request_addr(self, request_addr: str) -> Node:
        for node in self.validators + self.nodes:
            if node.host == request_addr:
                return node
        raise PoSException({"error": "Request came from unknown node"}, 400)
