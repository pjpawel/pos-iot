import logging
from collections import OrderedDict
from time import time
from uuid import UUID

from .block import Block
from .node import Node, NodeType
from .storage import BlocksStorage, NodeStorage, TransactionStorage, Storage, TransactionVerifiedStorage, \
    ValidatorStorage, ValidatorAgreementStorage, ValidatorAgreementInfoStorage, ValidatorAgreementResultStorage, \
    NodeTrustStorage, decode_chain, NodeTrustHistory
from .transaction import TxToVerify, TxVerified
from .trust import NodeTrustChange


class Manager:
    _storage: Storage

    def has_storage_files(self) -> bool:
        return self._storage.has_files()

    def has_empty_files(self) -> bool:
        return self._storage.is_empty()

    def get_storage(self):
        return self._storage


class BlockchainManager(Manager):
    _storage: BlocksStorage
    blocks: list[Block]

    def __init__(self):
        self._storage = BlocksStorage()
        self.blocks = self._storage.load()

    def add(self, block: Block) -> None:
        self.refresh()
        self.blocks.append(block)
        self._storage.update([block])

    def all(self) -> list[Block]:
        self.refresh()
        return self.blocks

    def blocks_to_dict(self) -> list[dict]:
        return [block.to_dict() for block in self.all()]

    def load_from_bytes(self, b: bytes) -> None:
        self.blocks = decode_chain(b)
        self._storage.dump(self.blocks)

    def get_last_block(self) -> Block:
        return self.all()[-1]

    def get_last_prev_hash(self) -> bytes:
        return self.get_last_block().prev_hash

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self.blocks = self._storage.load()


class TransactionToVerifyManager(Manager):
    _storage = TransactionStorage
    _txs: dict[UUID, TxToVerify]

    def __init__(self):
        self._storage = TransactionStorage()
        self._txs = self._storage.load()

    def add(self, identifier: UUID, tx: TxToVerify) -> None:
        self.refresh()
        self._txs[identifier] = tx
        self._storage.update({identifier: tx})

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self._txs = self._storage.load()

    def get(self, identifier: UUID) -> TxToVerify | None:
        self.refresh()
        return self._txs.get(identifier)

    def find(self, identifier: UUID) -> TxToVerify | None:
        self.refresh()
        return self._txs.get(identifier)

    def all(self) -> dict[UUID, TxToVerify]:
        self.refresh()
        return self._txs

    def pop(self, identifier: UUID) -> TxToVerify:
        self.refresh()
        try:
            self._storage.wait_for_set_lock()
            tx = self._txs.pop(identifier)
            self._storage.dump(self._txs, False)
            self._storage.unlock()
        except Exception as e:
            self._storage.unlock()
            raise e
        return tx

    def add_verification_result(self, identifier: UUID, node: Node, result: bool) -> None:
        tx = self.find(identifier)
        if not tx:
            raise Exception(f"Transaction {identifier.hex} not found")
        if tx.has_verification_result(node):
            logging.warning(f"Voting of transaction {identifier.hex} is already saved from node {node.identifier}")
            return
        self.refresh()
        try:
            self._storage.wait_for_set_lock()
            self._txs[identifier].voting[node.identifier] = result
            self._storage.dump(self._txs, False)
            self._storage.unlock()
        except Exception as e:
            self._storage.unlock()
            raise e
        logging.info(f"Successfully added verification result {result} from {node.identifier.hex}")


class NodeManager(Manager):
    _nodes: list[Node]
    _storage: NodeStorage

    def __init__(self):
        self._storage = NodeStorage()
        self._nodes = self._storage.load()

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self._nodes = self._storage.load()

    def to_dict(self) -> list[dict]:
        return [node.__dict__ for node in self.all()]

    def add(self, node: Node) -> None:
        self.refresh()
        self._nodes.append(node)
        self._storage.update([node])

    def all(self) -> list[Node]:
        self.refresh()
        return self._nodes

    def len(self) -> int:
        self.refresh()
        return len(self._nodes)

    def find_by_identifier(self, identifier: UUID) -> Node | None:
        self.refresh()
        for node in self._nodes:
            if node.identifier == identifier:
                return node
        return None

    def find_by_request_addr(self, request_addr: str) -> Node | None:
        self.refresh()
        for node in self._nodes:
            if node.host == request_addr:
                return node
        return None

    def exclude_self_node(self, self_ip: str) -> None:
        self.refresh()
        for node in self._nodes:
            if node.host == self_ip:
                self._nodes.remove(node)
                self._storage.dump(self._nodes)
                return


class ValidatorManager(Manager):
    _storage: ValidatorStorage
    identifiers: list[UUID]

    def __init__(self):
        self._storage = ValidatorStorage()
        self.identifiers = self._storage.load()

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self.identifiers = self._storage.load()

    def set_validators(self, validators: list[UUID]) -> None:
        self.refresh()
        self.identifiers = validators
        self._storage.dump(self.identifiers)

    def set_nodes_type(self, nodes: list[Node]) -> None:
        self.refresh()
        for node in nodes:
            if node.identifier in self.identifiers:
                node.set_type(NodeType.VALIDATOR)

    def all(self) -> list[UUID]:
        self.refresh()
        return self.identifiers


class NodeTrust(Manager):
    _storage = NodeTrustStorage
    _trusts = {}

    BASIC_TRUST = 5000

    def __init__(self):
        self._storage = NodeTrustStorage()
        self._trusts = self._storage.load()

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self._trusts = self._storage.load()

    def add_new_node_trust(self, node: Node, trust: None | int = None):
        if trust is None:
            trust = self.BASIC_TRUST
        self.refresh()
        self._storage.update({node.identifier: trust})
        self._trusts[node.identifier] = trust

    def add_trust_to_node(self, node: Node, new_trust: int) -> None:
        self.refresh()
        trust = self._trusts.get(node.identifier)
        if trust is None:
            self.add_new_node_trust(node)
            self.refresh()
            trust = self._trusts.get(node.identifier)
        self._trusts[node.identifier] = trust + new_trust
        self._storage.dump(self._trusts)

    def get_node_trust(self, node: Node) -> int:
        self.refresh()
        trust = self._trusts.get(node.identifier)
        if trust is None:
            self.add_new_node_trust(node)
            self.refresh()
            trust = self.BASIC_TRUST
        return trust


class TransactionVerifiedManager(Manager):
    _storage = TransactionVerifiedStorage
    _txs: dict[UUID, TxVerified]

    def __init__(self):
        self._storage = TransactionVerifiedStorage()
        self._txs = self._storage.load()

    def add(self, identifier: UUID, tx: TxVerified) -> None:
        self.refresh()
        self._txs[identifier] = tx
        self._storage.update({identifier: tx})

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self._txs = self._storage.load()

    def find(self, identifier: UUID) -> TxVerified | None:
        self.refresh()
        return self._txs.get(identifier)

    def all(self) -> dict[UUID, TxVerified]:
        self.refresh()
        return self._txs

    @staticmethod
    def sort_tx_by_time(txs: dict[UUID, TxVerified]) -> dict[UUID, TxVerified]:
        return OrderedDict(sorted(txs.items(), key=lambda item: item[1].time, reverse=True))

    def delete(self, identifiers: list[UUID]) -> list[TxVerified]:
        self.refresh()
        txs = []
        for ident in identifiers:
            txs.append(self._txs.pop(ident))
        self._storage.dump(self._txs)
        return txs


class ValidatorAgreementResult(Manager):
    _storage = ValidatorAgreementResultStorage
    _results = dict[UUID, bool]

    def __init__(self):
        self._storage = ValidatorAgreementResultStorage()
        self._results = self._storage.load()

    def add(self, identifier: UUID, result: bool) -> None:
        self.refresh()
        self._results[identifier] = result
        self._storage.update({identifier: result})

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self._results = self._storage.load()

    def find(self, identifier: UUID) -> bool | None:
        self.refresh()
        return self._results.get(identifier)

    def all(self) -> dict[UUID, bool]:
        self.refresh()
        return self._results

    def clear(self) -> None:
        self._results = {}
        self._storage.dump(self._results)


class ValidatorAgreement(Manager):
    _storage = ValidatorAgreementStorage
    uuids: list[UUID]

    def __init__(self):
        self._storage = ValidatorAgreementStorage()
        self.uuids = self._storage.load()

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self.uuids = self._storage.load()

    def all(self) -> list[UUID]:
        self.refresh()
        return self.uuids

    def set(self, uuids: list[UUID]) -> None:
        self.uuids = uuids
        self._storage.dump(self.uuids)


class ValidatorAgreementInfoManager(Manager):
    _storage = ValidatorAgreementInfoStorage
    is_started: bool
    last_successful_agreement: int
    leaders: list[UUID]

    def __init__(self):
        self._storage = ValidatorAgreementInfoStorage()
        if self._storage.is_empty():
            self.is_started = False
            self.last_successful_agreement = 0
            self.leaders = []
            self._storage.dump(self.prepare_info_data())
        else:
            data = self._storage.load()
            self.is_started = data["isStarted"]
            self.last_successful_agreement = data["last_successful_agreement"]
            self.leaders = [UUID(identifier) for identifier in data["leaders"]]

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        data = self._storage.load()
        self.is_started = data["isStarted"]
        self.last_successful_agreement = data["last_successful_agreement"]
        self.leaders = [UUID(identifier) for identifier in data["leaders"]]

    def set_info_data(self, is_started: bool, leaders: list[UUID]) -> None:
        self.refresh()
        self.is_started = is_started
        self.leaders = leaders
        self._storage.dump(self.prepare_info_data())

    def set_last_successful_agreement(self, last_successful_agreement: int):
        self.refresh()
        self.last_successful_agreement = last_successful_agreement
        self._storage.dump(self.prepare_info_data())

    def prepare_info_data(self) -> dict:
        return {
            "isStarted": self.is_started,
            "last_successful_agreement": self.last_successful_agreement,
            "leaders": [leader.hex for leader in self.leaders]
        }

    def add_leader(self, node: Node) -> None:
        self.refresh()
        self.leaders.append(node.identifier)


class NodeTrustHistoryManager(Manager):
    TRUST_PURGE_INTERVAL = 60

    _storage = NodeTrustHistory
    node_trusts: list[NodeTrustChange]

    def __init__(self):
        self._storage = NodeTrustHistory()
        self.node_trusts = self._storage.load()

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self.node_trusts = self._storage.load()

    def all(self) -> list[NodeTrustChange]:
        self.refresh()
        return self.node_trusts

    def set(self, node_trusts: list[NodeTrustChange]) -> None:
        self._storage.dump(node_trusts)
        self.node_trusts = node_trusts

    def purge_old_history(self) -> None:
        purge_timestamp = int(time()) - self.TRUST_PURGE_INTERVAL
        self.refresh()
        node_trusts_to_remove = []
        for node_trust in self.all():
            if node_trust.timestamp < purge_timestamp:
                node_trusts_to_remove.append(node_trust)

        if len(node_trusts_to_remove) > 0:
            node_trusts = list(set(self.node_trusts).difference(set(node_trusts_to_remove)))
            self.set(node_trusts)

    def has_node_trust(self, new_node_trust: NodeTrustChange) -> bool:
        self.refresh()
        for node_trust in self.all():
            if node_trust == new_node_trust:
                return True
        return False

    def add(self, node_trust: NodeTrustChange) -> None:
        self.refresh()
        self._storage.update([node_trust])
        self.node_trusts.append(node_trust)
