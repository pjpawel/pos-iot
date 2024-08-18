import logging
import os
import socket
from base64 import b64encode, b64decode
from io import BytesIO
from threading import Thread
from time import time
from uuid import uuid4, UUID

import requests

from .service import Blockchain, Node as NodeService, TransactionToVerify
from .storage import encode_chain, decode_chain
from .transaction import Tx, TxToVerify, TxVerified
from .node import Node, SelfNodeInfo, NodeType
from .request import Request
from .exception import PoTException
from .trust import NodeTrustChange, TrustChangeType


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
        logging.debug(f"=== Running as {name} ===")

        if self.nodes.find_by_identifier(self.self_node.identifier) is None:
            node = self.self_node.get_node()
            self.nodes.add(node)

        self.blockchain.refresh()
        self.nodes.refresh()
        self.tx_to_verified.refresh()

        if ip == genesis_ip:
            if len(self.blockchain.all()) == 0:
                self.blockchain.create_first_block(self.self_node)
            if self.nodes.count_validator_nodes() < 1:
                self.nodes.validators.set_validators([self.self_node.identifier])
        else:
            if len(self.nodes.all()) < 2 and not only_from_file:
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
        response = requests.get(f"http://{genesis_ip}:{5000}/node/update")
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
                f"Transaction not find in to verify {uuid.hex} from "
                f"{', '.join([uuid.hex for uuid in self.tx_to_verified.all().keys()])}")
            tx_verified = self.blockchain.find_tx_verified(uuid)
            if tx_verified:
                raise PoTException("Transaction already verified", 418)
            tx_bytes = None
            for validator_id in self.nodes.validators.all():
                validator_node = self.nodes.find_by_identifier(validator_id)
                logging.info(f"Getting transaction {uuid.hex} from node {validator_node.identifier.hex}")
                try:
                    tx_bytes = Request.send_transaction_get_info(validator_node.host, validator_node.port, uuid.hex)
                    break
                except Exception as e:
                    logging.warning(e)

            if not tx_bytes:
                raise PoTException("Cannot get transaction to verify from validators", 400)

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

        if len(tx_to_verified.voting) == self.nodes.count_validator_nodes():
            logging.info(f"Transaction {uuid.hex} voting")
            tx_to_verified = self.tx_to_verified.pop(uuid)

            nodes_positive, nodes_negative = tx_to_verified.get_voters_id_by_result()
            if tx_to_verified.is_voting_positive():
                tx_verified = tx_to_verified.get_verified_tx()
                self.blockchain.add_new_transaction(uuid, tx_verified)
                self.send_new_transaction_verified(uuid, tx_verified)
                self.send_multiple_trust_change(nodes_positive, TrustChangeType.TRANSACTION_VALIDATED, 20)
                self.send_multiple_trust_change(nodes_negative, TrustChangeType.TRANSACTION_VALIDATED, -40)
            else:
                logging.info(f"Transaction {uuid.hex} was rejected")
                self.send_multiple_trust_change(nodes_positive, TrustChangeType.TRANSACTION_VALIDATED, -40)
                self.send_multiple_trust_change(nodes_negative, TrustChangeType.TRANSACTION_VALIDATED, 20)

    def send_new_transaction_verified(self, identifier: UUID, tx_verified: TxVerified):
        data = str(tx_verified)

        def send(node: Node):
            logging.info(f"Sending verified transaction {identifier.hex} to node {node.identifier.hex} {data}")
            response = requests.post(f"http://{node.host}:{node.port}/transaction/{identifier.hex}/verified", data=data)
            if response.status_code != 200:
                logging.error(
                    f"Error while sending verified transaction {identifier.hex} to node {node.identifier.hex}. Error: {response.text}")

        threads = []
        for node in self.nodes.all():
            if node.identifier == self.self_node.identifier:
                continue
            th = Thread(target=send, args=[node])
            th.start()
            threads.append(th)

        # Wait for all to end
        while True:
            if len(threads) != 0:
                break
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)
        #self._send_to_all_nodes(send, [])

    def send_multiple_trust_change(self, nodes: list[Node | UUID], change_type: TrustChangeType, change: int):
        for node in nodes:
            if not isinstance(node, Node):
                node_id = node
                node = self.nodes.find_by_identifier(node_id)
                if not node:
                    raise Exception(f"Node not found with identifier {node_id.hex}")

            self.change_node_trust(node, change_type, change)

    def send_validators_list(self):
        data = {
            "validators": [identifier.hex for identifier in self.nodes.validators.all()]
        }
        logging.info("Available nodes to send new validators list: " + ', '.join(
            [node.identifier.hex for node in self.nodes.all()]))

        def send(node: Node):
            logging.info(f"Sending validators list to node {node.identifier.hex} {data}")
            response = requests.post(f"http://{node.host}:{node.port}/node/validator/new", json=data)
            if response.status_code != 200:
                logging.error(
                    f"Error while sending validators list to node {node.identifier.hex}. Error: {response.text}")

        threads = []
        for node in self.nodes.all():
            if node.identifier == self.self_node.identifier:
                continue
            th = Thread(target=send, args=[node])
            th.start()
            threads.append(th)

        # Wait for all to end
        while True:
            if len(threads) != 0:
                break
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)

    def change_node_trust(self, change_node: Node, change_type: TrustChangeType, change: int):
        node_trust = NodeTrustChange(change_node.identifier, int(time()), change_type, change)
        self.nodes.node_trust.add_trust_to_node(change_node, change)
        self.nodes.node_trust_history.add(node_trust)
        data = {
            "timestamp": node_trust.timestamp,
            "change": change,
            "type": change_type.value
        }

        def send_data(node: Node):
            try:
                Request.send_node_trust_change(node.host, node.port, change_node.identifier, data)
            except Exception as e:
                logging.error(e)

        threads = []
        for node in self.nodes.all():
            if node.identifier == self.self_node.identifier:
                continue
            th = Thread(target=send_data, args=[node])
            th.start()
            threads.append(th)

        # Wait for all to end
        while True:
            if len(threads) != 0:
                break
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)

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

    def transaction_verified_new(self, identifier: str, data: str, request_addr: str):
        tx_id = self._validate_create_uuid(identifier)
        self._validate_request_from_validator(request_addr)

        tx_verified = TxVerified.from_str(data)

        # Do not validate tx from validator
        # tx_node = self.nodes.find_by_identifier(tx_verified.tx.sender)
        # if not tx_node:
        #     raise PoTException(f"Node not found with identifier {tx_verified.tx.sender.hex}", 404)
        # if tx_node.host != request_addr:
        #     raise PoTException(f"Node hostname ({tx_node.host}) different than remote_addr: ({request_addr})", 400)
        # tx_verified.tx.validate(tx_node)

        self.blockchain.txs_verified.add(tx_id, tx_verified)

    def block_new(self, data: bytes, request_addr: str):
        self._validate_request_from_validator(request_addr)

        blocks = decode_chain(data)
        if len(blocks) == 1:
            raise PoTException("Blocks length is not 1", 400)
        new_block = blocks[0]

        blocks = self.blockchain.all()

        if blocks[-1].hash() != new_block.prev_hash:
            raise PoTException("Block hash does not equal prev hash", 400)

        # count = 1
        # while count < 100:
        #     if len(blocks) <= count:
        #         break
        #     block = blocks[-1*count]
        #     if new_block == block:
        #         raise PoTException("Block already registered", 400)

        self.blockchain.add(new_block)

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

    def add_new_block(self, data: bytes, request_addr: str):
        self._validate_request_from_validator(request_addr)
        block = decode_chain(data)[0]
        if block.prev_hash != self.blockchain.get_last_block().hash():
            raise PoTException("Prev hash does not match hash of previous block", 400)

        if self.nodes.is_validator(self.self_node.get_node()):
            txs_verified_with_ident = self.blockchain.txs_verified.sort_tx_by_time(self.blockchain.txs_verified.all())
            txs_verified = [tx_verified.tx for tx_verified in list(txs_verified_with_ident.values())]
            txs_verified_set = set(txs_verified)
            b_txs = set(block.transactions)
            # Check if all transactions in block are verified
            diff = b_txs.difference(txs_verified)
            if diff:
                raise PoTException(f"Transactions {', '.join([str(tx) for tx in diff])} are not verified", 400)
            diff = txs_verified_set.difference(b_txs)
            if diff:
                diff_count = []
                # Check if missing transactions are latest in verified list
                for tx in txs_verified:
                    if tx in diff:
                        diff_count.append(tx)
                    else:
                        diff_count = set(diff_count)
                        if diff_count != diff:
                            idents = []
                            for tx_diff in diff.difference(diff_count):
                                for ident, tx_verified in txs_verified_with_ident.items():
                                    if tx_verified.tx == tx_diff:
                                        idents.append(ident)
                                        break
                            txs_str = ', '.join([ident.hex for ident in idents])
                            raise PoTException(f"Transactions {txs_str} are not latest", 400)
                        break
            txs_verified_ids = []
            for tx_id, tx_verified in self.blockchain.txs_verified.all().items():
                if tx_verified.tx in block.transactions:
                    txs_verified_ids.append(tx_id)

            self.blockchain.txs_verified.delete(txs_verified_ids)
            self.blockchain.add(block)
            return "", 204

        block_hash = block.hash()
        for b in self.blockchain.all():
            if b.hash() == block_hash:
                return "Block is already in blockchain", 200
        # Remove transaction validated
        txs_verified_ids = []
        for tx_id, tx_verified in self.blockchain.txs_verified.all().items():
            if tx_verified.tx in block.transactions:
                txs_verified_ids.append(tx_id)

        self.blockchain.txs_verified.delete(txs_verified_ids)
        self.blockchain.add(block)
        return "", 204

    def populate_new_node(self, data: dict, request_addr: str) -> None:
        logging.info("Getting new node from " + request_addr)
        self._validate_request_from_validator(request_addr)

        self._validate_request_dict_keys(data, ["identifier", "host", "port"])
        identifier = self._validate_create_uuid(data.get("identifier"))
        host = data.get("host")
        port = int(data.get("port"))
        n_type = NodeType.SENSOR
        logging.info("Getting new node " + identifier.hex)

        # check if node is already register
        node_f = self.nodes.find_by_identifier(identifier)
        if node_f is not None:  # if node.host == host and node.port == port:
            raise Exception(f"Node is already registered with identifier: {node_f.identifier}")

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
            logging.info(f"Populating node {new_node.identifier.hex} to node {node.identifier}")
            res = requests.post(f"http://{node.host}:{node.port}/node/populate-new", json=data_to_send, timeout=15)
            logging.info(f"Response of populate {res.status_code} {res.text}")

        return data_to_send

    def node_update(self, data: dict) -> dict | tuple:
        self._validate_if_i_am_validator()
        logging.info(f"Updating nodes data {data}")

        last_block_hash = data.get("lastBlock", None)
        excluded_nodes = data.get("nodeIdentifiers", [])

        if last_block_hash is not None:
            blocks_to_show = []
            for block in self.blockchain.blocks[::-1]:
                blocks_to_show.append(block)
                if block.prev_hash == last_block_hash:
                    break
            blocks_to_show.reverse()
        else:
            blocks_to_show = self.blockchain.all()

        if excluded_nodes:
            nodes_to_show = []
            for node in self.nodes.all():
                if node.identifier.hex not in excluded_nodes:
                    nodes_to_show.append(node)
        else:
            nodes_to_show = self.nodes.all()

        return {
            "blockchain": b64encode(encode_chain(blocks_to_show)).hex(),
            "nodes": self.nodes.prepare_nodes_info(nodes_to_show)
        }

    def node_validator_agreement_get(self, remote_addr: str) -> dict:
        self._validate_if_i_am_validator()
        #self._validate_request_from_validator(remote_addr)
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

        is_started = self.nodes.is_agreement_started()
        if is_started:
            raise PoTException('Validator agreement already started', 400)

        leader = self._get_node_from_request_addr(remote_addr)
        if not self.nodes.is_validator(leader):
            raise PoTException('Leader is not a validator', 400)

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

        leader = self._get_node_from_request_addr(remote_addr)
        self.nodes.validator_agreement_info.set_info_data(True, [leader.identifier])
        self.nodes.validator_agreement.set(nodes)
        self.nodes.validator_agreement_result.add(leader.identifier, True)

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
        if not isinstance(vote, bool):
            raise PoTException("Vote result must be of type bool", 400)
        node = self._get_node_from_request_addr(remote_addr)
        if self.nodes.validator_agreement_result.find(node.identifier):
            raise PoTException("Vote result is already saved", 400)
        self.nodes.validator_agreement_result.add(node.identifier, vote)

        if self.nodes.is_agreement_voting_ended() and self.nodes.get_agreement_leader() == self.self_node.identifier:
            self.validator_agreement_end()

    def validator_agreement_end(self):
        new_leader = self.nodes.get_most_trusted_validator()
        new_validators = self.nodes.validator_agreement.all()
        self.nodes.clear_agreement_list()
        if self.nodes.is_agreement_result_success():
            self.nodes.validators.set_validators(new_validators)
            self.nodes.validator_agreement_info.set_last_successful_agreement(int(time()))
            self.nodes.validator_agreement_info.set_info_data(False, [])
            self.send_validators_list()
        else:
            self.nodes.validator_agreement_info.add_leader(new_leader)

        # done_data = {
        #     "validators": [vid.hex for vid in self.nodes.validator_agreement.all()],
        #     "leader": new_leader.identifier.hex
        # }
        #
        # def send(func):
        #     threads = []
        #     for node in self.nodes.all():
        #         if node.identifier == self.self_node.identifier or node.identifier not in self.nodes.validators.all():
        #             continue
        #         logging.info(
        #             f"Sending validator agreement done to host: {node.host}:{node.port} - starting thread")
        #         th = Thread(target=func, args=[node])
        #         th.start()
        #         threads.append(th)
        #
        #     # Wait for all to end
        #     while True:
        #         if len(threads) != 0:
        #             break
        #         for thread in threads:
        #             if not thread.is_alive():
        #                 threads.remove(thread)
        #
        # def done(node: Node):
        #     Request.send_validator_agreement_done(node.host, node.port, done_data)
        #
        # send(done)


    def node_validator_agreement_done(self, remote_addr: str, data: dict):
        self._validate_request_from_validator(remote_addr)
        logging.info(f"Validator agreement done {data}")
        self._validate_request_dict_keys(data, ["validators", "leader"])
        validator_list = [self._validate_create_uuid(ident) for ident in data.get("validators")]
        nodes_id_list = [node.identifier for node in self.nodes.all()]
        for validator_id in validator_list:
            if validator_id not in nodes_id_list:
                raise PoTException(f"Node {validator_id} is not node", 400)

        new_leader_id = self._validate_create_uuid(data.get("leader"))
        new_leader = self.nodes.find_by_identifier(new_leader_id)
        if new_leader is None:
            raise PoTException(f"Proposed new leader id ({new_leader_id}) is not found in nodes list", 400)
        if not self.nodes.is_validator(new_leader):
            raise PoTException(f"Proposed new leader ({new_leader_id}) is not validator", 400)

        self_node = self.nodes.find_by_identifier(self.self_node.identifier)
        if self.nodes.is_validator(self_node):
            if self.nodes.is_agreement_started() is False or len(self.nodes.validator_agreement.all()) > 0:
                raise PoTException("Agreement is not started or list is not send", 400)
            if validator_list != self.nodes.validator_agreement.all():
                raise PoTException("List is not the same as in agreement", 400)
            if not self.nodes.is_agreement_voting_ended():
                raise PoTException("Voting is not ended", 400)

        if self.nodes.is_agreement_result_success():
            self.nodes.validators.set_validators(validator_list)
            self.nodes.validator_agreement_info.set_last_successful_agreement(int(time()))
        else:
            new_leader_id = self._validate_create_uuid(data.get("leader"))
            new_leader = self.nodes.find_by_identifier(new_leader_id)
            if new_leader is None:
                raise PoTException(f"Proposed new leader id ({new_leader_id}) is not found in nodes list", 400)
            if not self.nodes.is_validator(new_leader):
                raise PoTException(f"Proposed new leader ({new_leader_id}) is not validator", 400)
            self.nodes.validator_agreement_info.add_leader(new_leader)

        self.nodes.clear_agreement_list()

    def node_new_validators(self, remote_addr: str, data: dict):
        self._validate_request_from_validator(remote_addr)
        self._validate_request_dict_keys(data, ["validators"])
        validators = data.get("validators")
        identifiers = []
        for ident in validators:
            uuid = self._validate_create_uuid(ident)
            node = self.nodes.find_by_identifier(uuid)
            if not node:
                msg = f"Unknown node of identifier {uuid}"
                logging.warning(msg)
                raise PoTException(msg, 400)
            identifiers.append(uuid)

        self.nodes.validators.set_validators(identifiers)
        # TODO: Reset validator agreement

    def node_trust_change(self, identifier: str, data: dict):
        self._validate_request_dict_keys(data, ["timestamp", "change", "type"])
        timestamp = int(data.get("timestamp"))
        change = int(data.get("change"))
        change_type = TrustChangeType(data.get("type"))
        node_id = self._validate_create_uuid(identifier)
        node = self.nodes.find_by_identifier(node_id)
        if not node:
            raise PoTException("Node not found with identifier " + node_id.hex, 404)
        self.nodes.node_trust_history.purge_old_history()
        node_trust = NodeTrustChange(node.identifier, timestamp, change_type, change)
        self.nodes.node_trust_history.add(node_trust)
        self.nodes.node_trust.add_trust_to_node(node, change)
        # if not self.nodes.node_trust_history.has_node_trust(node_trust):
        #     self.nodes.node_trust_history.add(node_trust)
        #     self.nodes.node_trust.add_trust_to_node(node, change)

    """
    Internal API methods (helpers)
    """

    def _validate_if_i_am_validator(self) -> None:
        if not self.nodes.is_validator(self._get_node_by_identifier(self.self_node.identifier)):
            raise PoTException("I am not validator", 400)

    def _validate_request_from_validator(self, request_addr: str) -> None:
        node = self.nodes.find_by_request_addr(request_addr)
        if not node:
            raise PoTException("Request came from unknown node", 400)
        if not self.nodes.is_validator(node):
            logging.info("Validators " + ', '.join([ident.hex for ident in self.nodes.validators.all()]))
            raise PoTException(f"Request came from node '{node.identifier.hex}' which is not validator", 400)

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
        if not isinstance(data, dict):
            raise PoTException("Given data: " + str(data) + " should be dict, but is type of " + str(type(data)), 400)
        data_keys = data.keys()
        if not set(keys).issubset(data_keys):
            raise PoTException("Missing required keys " + ', '.join(set(keys).difference(data_keys)), 400)

    def _send_to_all_nodes(self, func, args: list):
        threads = []
        for node in self.nodes.all():
            if node.identifier == self.self_node.identifier:
                continue
            args.append(node)
            th = Thread(target=func, args=args)
            th.start()
            threads.append(th)

        # Wait for all to end
        while True:
            if len(threads) != 0:
                break
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)
