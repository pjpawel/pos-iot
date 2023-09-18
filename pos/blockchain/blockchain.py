import logging
import os
import socket
from base64 import b64encode, b64decode
from io import BytesIO
from uuid import uuid4, UUID

import requests

from .manager import BlockchainManager, TransactionToVerifyManager, NodeManager
from .storage import encode_chain
from .transaction import Tx, TxToVerify
from .node import Node, SelfNode, NodeType
from .request import Request
from .exception import PoSException


class PoS:
    blockchain: BlockchainManager
    nodes: NodeManager
    tx_to_verified: TransactionToVerifyManager
    self_node: SelfNode

    def __init__(self):
        self.self_node = SelfNode.load(os.getenv("NODE_TYPE"))
        self.blockchain = BlockchainManager()
        self.nodes = NodeManager()
        self.tx_to_verified = TransactionToVerifyManager()

    def load(self, only_from_file: bool = False) -> None:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        genesis_ip = os.getenv("GENESIS_NODE")

        name = "genesis" if ip == genesis_ip else "node"
        logging.info(f"=== Running as {name} ===")

        if not self.nodes.has_empty_files():
            logging.info("Blockchain loading from storage")
            self.blockchain.refresh()
            self.nodes.refresh()
            self.tx_to_verified.refresh()
        elif ip != genesis_ip and not only_from_file:
            logging.info("Blockchain loading from genesis")
            self.load_from_validator_node(genesis_ip)
            identifier_hex = Request.get_info(genesis_ip, 5000).get("identifier")
            self.nodes.add(Node(identifier_hex, genesis_ip, 5000, NodeType.VALIDATOR))

        self.nodes.exclude_self_node(ip)

        if ip == genesis_ip and not self.blockchain.blocks:
            self.blockchain.create_first_block(self.self_node)

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
        self.nodes.update_from_json(response_json.get("nodes"))

    def send_transaction_populate(self, uuid: UUID, tx: Tx):
        tx_encoded = tx.encode()
        for node in self.nodes.all():
            if node.type == NodeType.VALIDATOR:
                if node.identifier == self.self_node.identifier:
                    continue
            try:
                Request.send_transaction_populate(node.host, node.port, uuid.hex, tx_encoded)
            except Exception as e:
                logging.error(f"Error while sending transaction populate to node {node.identifier.hex}. Error: {e}")

    def send_transaction_verification(self, uuid: UUID, verified: bool, message: str | None = None):
        data_to_send = {
            "result": verified,
            "message": message
        }
        for node in self.nodes.all():
            if node.identifier == self.self_node.identifier:
                continue
            try:
                Request.send_populate_verification_result(node.host, node.port, uuid.hex, data_to_send)
            except Exception as e:
                logging.error(f"Error while sending verification result to node {node.identifier.hex}. "
                              f"Transaction identifier: {uuid.hex} Result: {verified}. Error: {e}")

    def add_transaction_verification_result(self, uuid: UUID, node: Node, result: bool):
        tx_to_verified = self.tx_to_verified.find(uuid)
        if not tx_to_verified:
            logging.info(
                f"Transaction not find {uuid.hex} from "
                f"{', '.join([uuid.hex for uuid in self.tx_to_verified.all().keys()])}")
            logging.info(f"Getting transaction {uuid.hex} from node {node.identifier.hex}")
            tx_bytes = Request.send_transaction_get_info(node.host, node.port, uuid.hex)

            b = BytesIO(tx_bytes)
            tx = Tx.decode(b)
            tx_node = self._get_node_by_identifier(tx.sender)
            tx.validate(tx_node)
            self.tx_to_verified.add(uuid, TxToVerify(tx, tx_node))
            tx_to_verified = self.tx_to_verified.get(uuid)
            assert isinstance(tx_to_verified, TxToVerify)

        self.tx_to_verified.add_verification_result(uuid, node, result)
        tx_to_verified = self.tx_to_verified.find(uuid)
        logging.info(f"Printing result verification for transaction {uuid.hex}: {tx_to_verified.voting}")

        # n_validators = self.nodes.count_validator_nodes(self.self_node)
        # if tx_to_verified.is_ready_to_vote(n_validators):
        #     logging.info(f"Transaction {uuid.hex} voting")
        #     tx_to_verified = self.tx_to_verified.pop(uuid)
        #     assert isinstance(tx_to_verified, TxToVerify)
        #     if tx_to_verified.is_voting_positive():
        #         self.blockchain.add_new_transaction(tx_to_verified.tx)

        if len(tx_to_verified.voting) == self.nodes.count_validator_nodes(self.self_node):
            logging.info(f"Transaction {uuid.hex} voting")
            tx_to_verified = self.tx_to_verified.pop(uuid)
            assert isinstance(tx_to_verified, TxToVerify)
            if tx_to_verified.is_voting_positive():
                self.blockchain.add_new_transaction(tx_to_verified.tx)
            else:
                logging.info(f"Transaction {uuid.hex} was rejected")

    def node_validator_agreement_list_send(self):
        for node in self.nodes.all():
            if self.self_node.identifier == node.identifier:
                continue
            # Send validators list

    """
    API methods
    """

    def transaction_new(self, data: bytes, request_addr: str) -> dict:
        self._validate_if_i_am_validator()

        b = BytesIO(data)
        tx = Tx.decode(b)

        tx_node = self.nodes.find_by_identifier(tx.sender)
        if not tx_node:
            raise PoSException(f"Node not found with identifier {tx.sender.hex}", 404)
        if tx_node.host != request_addr:
            raise PoSException(f"Node hostname ({tx_node.host}) different than remote_addr: ({request_addr})", 400)

        tx.validate(tx_node)

        uuid = uuid4()
        self.tx_to_verified.add(uuid, TxToVerify(tx, tx_node))
        self.send_transaction_populate(uuid, tx)
        return {"id": uuid.hex}

    def transaction_get(self, identifier: str) -> bytes:
        self._validate_if_i_am_validator()
        uuid = self._validate_get_uuid(identifier)
        tx_to_verified = self.tx_to_verified.find(uuid)
        if not tx_to_verified:
            logging.info(
                f"Transaction not find {identifier} from "
                f"{', '.join([uuid.hex for uuid in self.tx_to_verified.all().keys()])}")
            raise PoSException(f"Cannot find transaction of given id {identifier}", 404)
        return tx_to_verified.tx.encode()

    def transaction_populate(self, data: bytes, identifier: str) -> None:
        uuid = self._validate_get_uuid(identifier)
        tx_to_verify = self.tx_to_verified.find(uuid)
        if tx_to_verify:
            logging.info(f"Transaction {uuid.hex} already registered")
            return

        tx = Tx.decode(BytesIO(data))
        tx_node = self.nodes.find_by_identifier(tx.sender)
        if not tx_node and self.self_node.identifier == tx.sender:
            tx_node = self.self_node
        if not tx_node:
            raise Exception(f"Node not found with identifier {tx.sender.hex}")

        tx.validate(tx_node)
        self.tx_to_verified.add(uuid, TxToVerify(tx, tx_node))

    def transaction_populate_verify_result(self, verified: bool, identifier: str, remote_addr: str):
        self._validate_request_from_validator(remote_addr)
        node = self._get_node_from_request_addr(remote_addr)
        uuid = self._validate_get_uuid(identifier)
        self.add_transaction_verification_result(uuid, node, verified)

    def populate_new_node(self, data: dict, request_addr: str) -> None:
        self._validate_request_from_validator(request_addr)

        identifier = self._validate_get_uuid(data.get("identifier"))
        host = data.get("host")
        port = int(data.get("port"))
        n_type = getattr(NodeType, data.get("type"))

        # check if node is already register
        for node in self.nodes.all():
            if node.host == host and node.port == port:
                raise Exception(f"Node is already registered with identifier: {node.identifier}")

        self.nodes.add(Node(identifier, host, port, n_type))

    def node_register(self, identifier: UUID, node_ip: str, port: int, n_type: NodeType) -> dict | tuple:
        self._validate_if_i_am_validator()

        for node in self.nodes.all():
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
        for node in self.nodes.get_validator_nodes():
            requests.post(f"http://{node.host}:{node.port}/node/populate-new", data_to_send, timeout=15.0)

        self.nodes.add(new_node)
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
            for node in self.nodes.all():
                if node.identifier.hex not in excluded_nodes:
                    nodes_to_show.append(node)

        blocks_encoded = encode_chain(blocks_to_show or self.blockchain.blocks)
        return {
            "blockchain": b64encode(blocks_encoded).hex(),
            "nodes": [node.__dict__ for node in nodes_to_show or self.nodes.all()]
        }

    def node_validator_agreement_get(self):
        pass

    def node_validator_agreement_start(self):
        pass

    def node_validator_agreement_list_get(self):
        pass

    def node_validator_agreement_list_set(self):
        pass

    def node_validator_agreement_accept(self):
        pass

    def node_validator_agreement_done(self):
        pass

    """
    Internal API methods
    """

    def _validate_if_i_am_validator(self) -> None:
        if not self.self_node.type == NodeType.VALIDATOR:
            raise PoSException("I am not validator", 400)

    def _validate_request_from_validator(self, request_addr: str) -> None:
        node = self.nodes.find_by_request_addr(request_addr)
        if not node:
            raise PoSException("Request came from unknown node", 400)
        if not node.type == NodeType.VALIDATOR:
            raise PoSException("Request came from node which is not validator", 400)

    def _get_node_from_request_addr(self, request_addr: str) -> Node:
        node = self.nodes.find_by_request_addr(request_addr)
        if not node:
            raise PoSException("Request came from unknown node", 400)
        return node

    def _get_node_by_identifier(self, identifier: UUID) -> Node:
        if self.self_node.identifier == identifier:
            return self.self_node
        node = self.nodes.find_by_identifier(identifier)
        if not node:
            raise Exception(f"Node {identifier.hex} was not found")

    def _validate_get_uuid(self, identifier: str) -> UUID:
        try:
            return UUID(identifier)
        except:
            msg = f"Identifier {identifier} is not valid UUID"
            logging.info(msg)
            raise PoSException(msg, 400)
