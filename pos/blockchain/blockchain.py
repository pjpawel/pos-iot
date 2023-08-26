import logging
import os
import json
import socket
from base64 import b64encode, b64decode
from hashlib import sha256
from io import BytesIO
from typing import BinaryIO, IO
from uuid import uuid4, UUID
from sys import getsizeof

import requests

from .block import Block, BlockCandidate
from pos.network.peer import Handler
from .transaction import Tx, TxToVerify
from .utils import is_file, is_dir
from .node import Node, SelfNode, NodeType
from .request import get_info, send_populate_verification_result, send_transaction_populate, send_transaction_get_info
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
        return [block.to_dict() for block in self.blocks]


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
            self.nodes.append(Node(identifier_hex, genesis_ip, 5000, NodeType.VALIDATOR))

        self._exclude_self_node(ip)

        if ip == genesis_ip and not self.blockchain.blocks:
            self.blockchain.create_first_block(self.self_node)

    def nodes_to_dict(self) -> list[dict]:
        return [node.__dict__ for node in self.nodes]

    """
    Internal methods
    """

    def load_from_validator_node(self, genesis_ip: str) -> None:
        data = {
            "identifier": self.self_node.identifier.hex,
            "port": 5000,
            "type": self.self_node.type.name
        }
        logging.info("Registering node")
        response = requests.post(f"http://{genesis_ip}:{5000}/node/register", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}. Code: {response.status_code} "
                            f"Response data: " + response.text)
        self.update_from_validator_node(genesis_ip)

    def update_from_validator_node(self, genesis_ip: str) -> None:
        data = {"port": 5000}
        response = requests.post(f"http://{genesis_ip}:{5000}/node/update", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000} Code: {response.status_code} "
                            f"Response data: " + response.text)
        response_json = response.json()
        self.blockchain.load_from_bytes(b64decode(bytes.fromhex(response_json.get("blockchain"))))
        self.nodes = [Node.load_from_dict(data) for data in response_json.get("nodes")]

    def send_transaction_populate(self, uuid: UUID, tx: Tx):
        tx_encoded = tx.encode()
        for node in self.nodes:
            if node.type == NodeType.VALIDATOR:
                if node.identifier == self.self_node.identifier:
                    continue
            try:
                send_transaction_populate(node.host, node.port, uuid.hex, tx_encoded)
            except Exception as e:
                logging.error(f"Error while sending transaction populate to node {node.identifier.hex}. Error: {e}")

    def send_transaction_verification(self, uuid: UUID, verified: bool, message: str | None = None):
        data_to_send = {
            "result": verified,
            "message": message
        }
        for node in self.nodes:
            if node.type == NodeType.VALIDATOR:
                if node.identifier == self.self_node.identifier:
                    continue
                try:
                    send_populate_verification_result(node.host, node.port, uuid.hex, data_to_send)
                except Exception as e:
                    logging.error(f"Error while sending verification result to node {node.identifier.hex}. "
                                  f"Transaction identifier: {uuid.hex} Result: {verified}. Error: {e}")

    def add_transaction_verification_result(self, uuid: UUID, node: Node, result: bool):
        tx_to_verified = self.tx_to_verified.get(uuid)
        if not tx_to_verified:
            logging.info(
                f"Transaction not find {uuid.hex} from {', '.join([uuid.hex for uuid in self.tx_to_verified.keys()])}")
            logging.info(f"Getting transaction {uuid.hex} from node {node.identifier.hex}")
            tx_bytes = send_transaction_get_info(node.host, node.port, uuid.hex)

            b = BytesIO(tx_bytes)
            tx = Tx.decode(b)
            tx_node = self._get_node_by_identifier(tx.sender)
            tx.validate(tx_node)
            self.tx_to_verified[uuid] = TxToVerify(tx, tx_node)
            tx_to_verified = self.tx_to_verified.get(uuid)
            assert isinstance(tx_to_verified, TxToVerify)

        tx_to_verified.add_verification_result(node, result)
        logging.info(f"Printing result verification for transaction {uuid.hex}: {tx_to_verified.voting}")

        if len(tx_to_verified.voting) == self._count_validator_nodes():
            logging.info(f"Transaction {uuid.hex} voting")
            tx_to_verified = self.tx_to_verified.pop(uuid)
            assert isinstance(tx_to_verified, TxToVerify)
            if tx_to_verified.is_voting_positive():
                self.blockchain.add_new_transaction(tx_to_verified.tx, tx_to_verified.node)

    def _has_storage_files(self) -> bool:
        return is_dir(self._storage_dir) \
            and is_file(os.path.join(self._storage_dir, self.BLOCKCHAIN_PATH)) \
            and is_file(os.path.join(self._storage_dir, self.NODES_PATH))

    def _exclude_self_node(self, self_ip: str) -> None:
        for node in self.nodes:
            if node.host == self_ip:
                self.nodes.remove(node)
                return

    def _load_from_storage(self) -> None:
        with open(os.path.join(self._storage_dir, self.BLOCKCHAIN_PATH), "rb") as f:
            self.blockchain.load_from_file(f)
        with open(os.path.join(self._storage_dir, self.NODES_PATH)) as f:
            self.nodes = json.load(f)

    def _dump_to_storage(self) -> None:
        with open(os.path.join(self._storage_dir, self.BLOCKCHAIN_PATH), 'wb') as f:
            f.write(encode_chain(self.blockchain.blocks))
        with open(os.path.join(self._storage_dir, self.NODES_PATH), 'w') as f:
            json.dump(self.nodes, f)

    def _count_validator_nodes(self) -> int:
        count = 0
        for node in self.nodes:
            if node.type == NodeType.VALIDATOR:
                count += 1
        if self.self_node.type == NodeType.VALIDATOR:
            count += 1
        return count

    # def __del__(self):
    #     self._dump_to_storage()

    """
    API methods
    """

    def transaction_new(self, data: bytes, request_addr: str) -> dict:
        self._validate_if_i_am_validator()

        b = BytesIO(data)
        tx = Tx.decode(b)

        # TODO: change to _get_node...
        tx_node = None
        for node in self.nodes:
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

        self.send_transaction_populate(uuid, tx)

        return {"id": uuid.hex}

    def transaction_get(self, identifier: str) -> bytes:
        self._validate_if_i_am_validator()

        uuid = UUID(identifier)
        tx_to_verified = self.tx_to_verified.get(uuid)
        if not tx_to_verified:
            logging.info(
                f"Transaction not find {identifier} from {', '.join([uuid.hex for uuid in self.tx_to_verified.keys()])}")
            raise PoSException(f"Cannot find transaction of given id {identifier}", 404)

        return tx_to_verified.tx.encode()

    def transaction_populate(self, data: bytes, identifier: str) -> None:
        uuid = UUID(identifier)

        tx_to_verify = self.tx_to_verified.get(uuid)
        if tx_to_verify:
            logging.info(f"Transaction {uuid.hex} already registered")
            return

        tx = Tx.decode(BytesIO(data))

        # TODO change to _get_node_by_id
        tx_node = None
        for node in self.nodes + [self.self_node]:
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
        self.add_transaction_verification_result(uuid, node, verified)

    def populate_new_node(self, data: dict, request_addr: str) -> None:
        self._validate_request_from_validator(request_addr)

        identifier = data.get("identifier")
        host = data.get("host")
        port = int(data.get("port"))
        n_type = getattr(NodeType, data.get("type"))

        # check if node is already register
        for node in self.nodes:
            if node.host == host and node.port == port:
                raise Exception(f"Node is already registered with identifier: {node.identifier}")

        self.nodes.append(Node(identifier, host, port, n_type))

    def node_register(self, identifier: UUID, node_ip: str, port: int, n_type: NodeType) -> dict | tuple:
        self._validate_if_i_am_validator()

        for node in self.nodes:
            if node.host == node_ip and node.port == port:
                return {"error": f"Node is already registered with identifier: {node.identifier}"}, 400

        new_node = Node(identifier, node_ip, 5000, n_type)
        data_to_send = {
            "identifier": new_node.identifier.hex,
            "host": new_node.host,
            "port": new_node.port,
            "type": n_type
        }

        # Populate nodes
        for node in self.nodes:
            if node.type == NodeType.VALIDATOR:
                requests.post(f"http://{node.host}:{node.port}/node/populate-new", data_to_send, timeout=15.0)

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
            for node in self.nodes:
                if node.identifier.hex not in excluded_nodes:
                    nodes_to_show.append(node)

        blocks_encoded = encode_chain(blocks_to_show or self.blockchain.blocks)
        return {
            "blockchain": b64encode(blocks_encoded).hex(),
            "nodes": [node.__dict__ for node in nodes_to_show or self.nodes]
        }

    """
    Internal API methods
    """

    def _validate_if_i_am_validator(self) -> None:
        if not self.self_node.type == NodeType.VALIDATOR:
            raise PoSException("I am not validator", 400)

    def _validate_request_from_validator(self, request_addr: str) -> None:
        validator = False
        for node in self.nodes:
            if node.type == NodeType.VALIDATOR and node.host == request_addr:
                validator = True

        if not validator:
            raise PoSException("Request came from node which is not validator", 400)

    def _get_node_from_request_addr(self, request_addr: str) -> Node:
        for node in self.nodes:
            if node.host == request_addr:
                return node
        raise PoSException("Request came from unknown node", 400)

    def _get_node_by_identifier(self, identifier: UUID) -> Node:
        if self.self_node.identifier == identifier:
            return self.self_node
        for node in self.nodes:
            if node.identifier == identifier:
                return node
        raise Exception(f"Node {identifier.hex} was not found")
