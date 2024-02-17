import logging
import os
import socket
from base64 import b64encode, b64decode
from io import BytesIO
from time import time
from uuid import uuid4, UUID

import requests

from .service import Blockchain, Node as NodeService, TransactionToVerify
from .storage import encode_chain
from .transaction import Tx, TxToVerify
from .node import Node, SelfNodeInfo, NodeType
from .request import Request
from .exception import PoTException


class PoT:
    blockchain: Blockchain
    nodes: NodeService
    tx_to_verified: TransactionToVerify
    self_node: SelfNodeInfo

    def __init__(self):
        self.self_node = SelfNodeInfo()
        self.blockchain = Blockchain()
        self.nodes = NodeService()
        self.tx_to_verified = TransactionToVerify()

    def load(self, only_from_file: bool = False) -> None:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        genesis_hostname = os.getenv("GENESIS_NODE")
        genesis_ip = socket.gethostbyname(genesis_hostname)

        name = "genesis" if ip == genesis_ip else "node"
        logging.info(f"=== Running as {name} ===")

        if self.nodes.find_by_identifier(self.self_node.identifier) is None:
            node = self.self_node.get_node()
            self.nodes.add(node)

        self.blockchain.refresh()
        self.nodes.refresh()
        self.tx_to_verified.refresh()

        if ip == genesis_ip:
            if len(self.blockchain.all()) == 0:
                self.blockchain.create_first_block(self.self_node)
            self.nodes.validators.set_validators([self.self_node.identifier])
        else:
            if not only_from_file:
                logging.info("Blockchain loading from genesis")
                identifier_hex = Request.get_info(genesis_ip, 5000).get("identifier")
                genesis_node = Node(identifier_hex, genesis_ip, 5000, NodeType.VALIDATOR)
                self.nodes.add(genesis_node)
                self.nodes.validators.set_validators([genesis_node.identifier])
                self.load_from_validator_node(genesis_ip)

    """
    Internal methods
    """

    def is_self_node_is_registered(self, genesis_ip: str) -> bool:
        response = requests.get(f"http://{genesis_ip}:{5000}/node/{self.self_node.identifier.hex}")
        return response.status_code == 200

    def load_from_validator_node(self, genesis_ip: str) -> None:
        if self.is_self_node_is_registered(genesis_ip):
            return
        node = self.nodes.find_by_identifier(self.self_node.identifier)
        data = {
            "identifier": node.identifier.hex,
            "port": 5000,
            "type": node.type.name
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
            raise Exception(f"Cannot update from genesis node: {genesis_ip}:{5000} Code: {response.status_code} "
                            f"Response data: " + response.text)
        response_json = response.json()
        self.blockchain.load_from_bytes(b64decode(bytes.fromhex(response_json.get("blockchain"))))
        self.nodes.update_from_json(response_json.get("nodes"))

    def send_transaction_populate(self, uuid: UUID, tx: Tx):
        tx_encoded = tx.encode()
        for node in self.nodes.get_validator_nodes():
            try:
                Request.send_transaction_populate(node.host, node.port, uuid.hex, tx_encoded)
            except Exception as e:
                logging.error(f"Error while sending transaction populate to node {node.identifier.hex}. Error: {e}")

    def send_transaction_verification(self, uuid: UUID, verified: bool, message: str | None = None):
        data_to_send = {
            "result": verified,
            "message": message
        }
        for node in self.nodes.get_validator_nodes():
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

        if len(tx_to_verified.voting) == self.nodes.count_validator_nodes():
            logging.info(f"Transaction {uuid.hex} voting")
            tx_to_verified = self.tx_to_verified.pop(uuid)
            assert isinstance(tx_to_verified, TxToVerify)
            if tx_to_verified.is_voting_positive():
                self.blockchain.add_new_transaction(uuid, tx_to_verified.get_verified_tx())
            else:
                logging.info(f"Transaction {uuid.hex} was rejected")

    def node_validator_agreement_list_send(self):
        for node in self.nodes.all():
            if self.self_node.identifier == node.identifier:
                continue
            # TODO: Send validators list

    """
    API methods
    """

    def transaction_new(self, data: bytes, request_addr: str) -> dict:
        self._validate_if_i_am_validator()

        b = BytesIO(data)
        tx = Tx.decode(b)

        tx_node = self.nodes.find_by_identifier(tx.sender)
        if not tx_node:
            raise PoTException(f"Node not found with identifier {tx.sender.hex}", 404)
        if tx_node.host != request_addr:
            raise PoTException(f"Node hostname ({tx_node.host}) different than remote_addr: ({request_addr})", 400)

        tx.validate(tx_node)

        uuid = uuid4()
        self.tx_to_verified.add(uuid, TxToVerify(tx, tx_node))
        self.send_transaction_populate(uuid, tx)
        return {"id": uuid.hex}

    def transaction_get(self, identifier: str) -> bytes:
        self._validate_if_i_am_validator()
        uuid = self._validate_create_uuid(identifier)
        tx_to_verified = self.tx_to_verified.find(uuid)
        if not tx_to_verified:
            logging.info(
                f"Transaction not find {identifier} from "
                f"{', '.join([uuid.hex for uuid in self.tx_to_verified.all().keys()])}")
            raise PoTException(f"Cannot find transaction of given id {identifier}", 404)
        return tx_to_verified.tx.encode()

    def transaction_populate(self, data: bytes, identifier: str) -> None:
        uuid = self._validate_create_uuid(identifier)
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
        uuid = self._validate_create_uuid(identifier)
        self.add_transaction_verification_result(uuid, node, verified)

    def populate_new_node(self, data: dict, request_addr: str) -> None:
        self._validate_request_from_validator(request_addr)

        self._validate_request_dict_keys(data, ["identifier", "host", "port", "type"])
        identifier = self._validate_create_uuid(data.get("identifier"))
        host = data.get("host")
        port = int(data.get("port"))
        #n_type = getattr(NodeType, data.get("type"))
        n_type = NodeType.SENSOR

        # check if node is already register
        node_f = self.nodes.find_by_identifier(identifier)
        if node_f is not None:
        #if node.host == host and node.port == port:
            raise Exception(f"Node is already registered with identifier: {node.identifier}")

        self.nodes.add(Node(identifier, host, port, n_type))

    def node_register(self, identifier: UUID, node_ip: str, port: int, n_type: NodeType) -> dict | tuple:
        self._validate_if_i_am_validator()

        for node in self.nodes.all():
            if node.host == node_ip and node.port == port:
                raise PoTException(f"Node is already registered with identifier: {node.identifier}", 400)

        new_node = Node(identifier, node_ip, 5000, n_type)
        self.nodes.add(new_node)

        # Populate to all nodes
        data_to_send = {
            "identifier": new_node.identifier.hex,
            "host": new_node.host,
            "port": new_node.port,
            #"type": n_type.value
        }
        for node in self.nodes.all():
            if node.identifier == new_node.identifier or node.identifier == self.self_node.identifier:
                continue
            requests.post(f"http://{node.host}:{node.port}/node/populate-new", json=data_to_send, timeout=15)

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
            "nodes": self.nodes.prepare_nodes_info(nodes_to_show or self.nodes.all())
        }

    def node_validator_agreement_get(self, remote_addr: str) -> dict:
        self._validate_if_i_am_validator()
        self._validate_request_from_validator(remote_addr)
        is_started = self.nodes.is_agreement_started()
        data = {
            "isStarted": is_started
        }
        if is_started:
            data["leader"] = self.nodes.get_agreement_leader().hex
            data["list"] = [node.hex for node in self.nodes.get_agreement_list()]
        return data

    def node_validator_agreement_start(self, remote_addr: str, data: dict):
        self._validate_if_i_am_validator()
        self._validate_request_from_validator(remote_addr)

        leader = self._get_node_from_request_addr(remote_addr)
        if not self.nodes.is_validator(leader):
            raise PoTException('Leader is not a validator', 400)

        is_started = self.nodes.is_agreement_started()
        if is_started:
            raise PoTException('Validator agreement already stared', 400)

        node_ids = data.get("list")
        if not node_ids:
            raise PoTException("Missing list from request", 400)
        nodes = []
        for node_id in node_ids:
            uid = self._validate_create_uuid(node_id)
            self._get_node_by_identifier(uid)
            nodes.append(uid)

        if self.nodes.calculate_validators_number() != len(nodes):
            raise PoTException("Validator number is not correct", 400)

        self.nodes.validator_agreement_info.set_info_data(True, nodes)

        return {
            "isStarted": is_started,
            "leader": self.nodes.get_agreement_leader().hex,
            "list": [node.hex for node in self.nodes.get_agreement_list()]
        }

    def node_validator_agreement_list_set(self, uuids: list[UUID]):
        valid_id_nodes = set(uuids).intersection(set(self.nodes.all()))
        if len(valid_id_nodes) == len(uuids):
            raise PoTException("Invalid validator agreement list", 400)
            # TODO: is correct
        self.nodes.set_agreement_list(uuids)

    def node_validator_agreement_vote(self, remote_addr: str, data: dict):
        vote = data.get("result")
        if vote is None:
            raise PoTException("Missing vote result", 400)
        node = self._get_node_from_request_addr(remote_addr)
        # TODO: to be completed

    def node_validator_agreement_done(self):
        if self.nodes.is_agreement_started() is False or len(self.nodes.validator_agreement.all()) > 0:
            raise PoTException("Agreement is not started or list is not send", 400)

        if not self.nodes.is_agreement_voting_ended():
            raise PoTException("Voting is not ended", 400)

        self.nodes.clear_agreement_list()
        if self.nodes.is_agreement_result_success():
            self.nodes.validators.set_validators(self.nodes.validator_agreement.all())
            self.nodes.validator_agreement_info.set_last_successful_agreement(int(time()))
        else:
            self.nodes.validator_agreement_info.add_leader(self.nodes.get_most_trusted_validator())

    """
    Internal API methods
    """

    def _validate_if_i_am_validator(self) -> None:
        if not self.nodes.is_validator(self._get_node_by_identifier(self.self_node.identifier)):
            raise PoTException("I am not validator", 400)

    def _validate_request_from_validator(self, request_addr: str) -> None:
        node = self.nodes.find_by_request_addr(request_addr)
        if not node:
            raise PoTException("Request came from unknown node", 400)
        if not node.type == NodeType.VALIDATOR:
            raise PoTException("Request came from node which is not validator", 400)

    def _get_node_from_request_addr(self, request_addr: str) -> Node:
        node = self.nodes.find_by_request_addr(request_addr)
        if not node:
            raise PoTException("Request came from unknown node", 400)
        return node

    def _get_node_by_identifier(self, identifier: UUID) -> Node:
        node = self.nodes.find_by_identifier(identifier)
        if not node:
            raise Exception(f"Node {identifier.hex} was not found")
        return node

    def _validate_create_uuid(self, identifier: str) -> UUID:
        try:
            return UUID(identifier)
        except:
            msg = f"Identifier {identifier} is not valid UUID"
            logging.info(msg)
            raise PoTException(msg, 400)

    def _validate_request_dict_keys(self, data: dict, keys: list[str]) -> None:
        data_keys = data.keys()
        if not set(keys).issubset(data_keys):
            raise PoTException("Missing required keys " + ', '.join(set(keys).difference(data_keys)), 400)
