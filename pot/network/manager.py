import logging
from hashlib import sha256
from uuid import UUID

from .block import Block, BlockCandidate
from .node import SelfNode, Node, NodeType
from .storage import BlocksStorage, NodeStorage, TransactionStorage, Storage, TransactionVerifiedStorage, \
    ValidatorStorage, ValidatorAgreementStorage, ValidatorAgreementInfoStorage
from .transaction import TxToVerify, Tx, TxVerified


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
        self.blocks = []
        self._storage = BlocksStorage()

    def create_first_block(self, self_node: SelfNode) -> None:
        block = BlockCandidate.create_new([])
        self.add(block.sign(
            sha256(b'0000000000').digest(),
            self_node.identifier,
            self_node.private_key
        ))

    def add(self, block: Block) -> None:
        if not self._storage.is_up_to_date():
            self.refresh()
        self.blocks.append(block)
        self._storage.update([block])

    def blocks_to_dict(self) -> list[dict]:
        return [block.to_dict() for block in self.blocks]

    def load_from_bytes(self, b: bytes) -> None:
        self._storage.load_from_bytes(b)

    def refresh(self) -> None:
        self.blocks = [] if self._storage.is_empty() else self._storage.load()


class TransactionToVerifyManager(Manager):
    _storage = TransactionStorage
    _txs: dict[UUID, TxToVerify]

    def __init__(self):
        self._txs = {}
        self._storage = TransactionStorage()

    def add(self, identifier: UUID, tx: TxToVerify) -> None:
        if not self._storage.is_up_to_date():
            self.refresh()
        self._txs[identifier] = tx
        self._storage.update({identifier: tx})

    def refresh(self) -> None:
        self._txs = {} if self._storage.is_empty() else self._storage.load()

    def get(self, identifier: UUID) -> TxToVerify | None:
        if not self._storage.is_up_to_date():
            self.refresh()
        return self._txs.get(identifier)

    def find(self, identifier: UUID) -> TxToVerify | None:
        if not self._storage.is_up_to_date():
            self.refresh()
        return self._txs.get(identifier)

    def all(self) -> dict[UUID, TxToVerify]:
        if not self._storage.is_up_to_date():
            self.refresh()
        return self._txs

    def pop(self, identifier: UUID) -> TxToVerify:
        if not self._storage.is_up_to_date():
            self.refresh()
        try:
            self._storage.wait_for_set_lock()
            txs = self._txs.pop(identifier)
            self._storage.dump(self._txs, False)
            self._storage.unlock()
        except Exception as e:
            self._storage.unlock()
            raise e
        return txs

    def add_verification_result(self, identifier: UUID, node: Node, result: bool) -> None:
        tx = self.find(identifier)
        if not tx:
            raise Exception(f"Transaction {identifier.hex} not found")
        if tx.has_verification_result(node):
            logging.warning(f"Voting is already saved from node {node.identifier}")
            return
        if not self._storage.is_up_to_date():
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
    _validator_storage: ValidatorStorage

    def __init__(self):
        self._nodes = []
        self._storage = NodeStorage()
        self._validator_storage = ValidatorStorage()

    def to_dict(self) -> list[dict]:
        return [node.__dict__ for node in self._nodes]

    def add(self, node: Node) -> None:
        if not self._storage.is_up_to_date():
            self.refresh()
        self._nodes.append(node)
        self._storage.update([node])

    def all(self) -> list[Node]:
        if not self._storage.is_up_to_date():
            self.refresh()
        return self._nodes

    def len(self) -> int:
        if not self._storage.is_up_to_date():
            self.refresh()
        return len(self._nodes)

    def find_by_identifier(self, identifier: UUID) -> Node | None:
        if not self._storage.is_up_to_date():
            self.refresh()
        for node in self._nodes:
            if node.identifier == identifier:
                return node
        return None

    def find_by_request_addr(self, request_addr: str) -> Node | None:
        if not self._storage.is_up_to_date():
            self.refresh()
        for node in self._nodes:
            if node.host == request_addr:
                return node
        return None

    def update_from_json(self, nodes_dict: list[dict]) -> None:
        self._nodes = [Node.load_from_dict(data) for data in nodes_dict]
        self._storage.dump(self._nodes)

    def get_validator_nodes(self) -> list[Node]:
        if not self._storage.is_up_to_date():
            self.refresh()
        validators = []
        for node in self._nodes:
            if node.type == NodeType.VALIDATOR:
                validators.append(node)
        return validators

    def refresh(self) -> None:
        if self._storage.is_up_to_date():
            return
        self._nodes = [] if self._storage.is_empty() else self._storage.load()
        self._update_validators()

    def count_validator_nodes(self, self_node: SelfNode) -> int:
        if not self._storage.is_up_to_date():
            self.refresh()
        count = 0
        for node in self._nodes:
            if node.type == NodeType.VALIDATOR:
                count += 1
        if self_node.type == NodeType.VALIDATOR:
            count += 1
        return count

    def exclude_self_node(self, self_ip: str) -> None:
        if not self._storage.is_up_to_date():
            self.refresh()
        for node in self._nodes:
            if node.host == self_ip:
                self._nodes.remove(node)
                self._storage.dump(self._nodes)
                return

    def set_validators(self, validators: list[UUID]) -> None:
        self._validator_storage.dump(validators)
        self._validator_storage.invalidate_cache()
        self.refresh()

    def _update_validators(self) -> None:
        if self._validator_storage.is_up_to_date():
            return
        validators_id = self._validator_storage.load()
        for node in self._nodes:
            node.set_type(NodeType.VALIDATOR if node.identifier in validators_id else NodeType.SENSOR)


class TransactionVerifiedManager(Manager):
    _storage = TransactionVerifiedStorage
    _txs: dict[UUID, TxVerified]

    def __init__(self):
        self._txs = {}
        self._storage = TransactionVerifiedStorage()

    def add(self, identifier: UUID, tx: TxVerified) -> None:
        if not self._storage.is_up_to_date():
            self.refresh()
        self._txs[identifier] = tx
        self._storage.update({identifier: tx})

    def refresh(self) -> None:
        self._txs = {} if self._storage.is_empty() else self._storage.load()

    def find(self, identifier: UUID) -> TxVerified | None:
        if not self._storage.is_up_to_date():
            self.refresh()
        return self._txs.get(identifier)

    def all(self) -> dict[UUID, TxVerified]:
        if not self._storage.is_up_to_date():
            self.refresh()
        return self._txs

    def delete(self, identifiers: list) -> list[TxVerified]:
        # TODO:
        pass


class ValidatorAgreement(Manager):
    _storage = ValidatorAgreementStorage
    _storage_info = ValidatorAgreementInfoStorage
    is_started: bool
    last_successful_agreement: int
    leaders: list[UUID]
    uuids: list[UUID]

    def __init__(self):
        self._storage = ValidatorAgreementStorage()
        self._storage_info = ValidatorAgreementInfoStorage()
        self.uuids = []
        if self._storage_info.is_empty():
            self.is_started = False
            self.last_successful_agreement = 0
            self.leaders = []
            self._storage_info.dump(self.prepare_info_data())
        self.refresh_info()

    def refresh_list(self) -> None:
        if self._storage_info.is_up_to_date():
            return
        self.uuids = [] if self._storage.is_empty() else self._storage.load()

    def refresh_info(self) -> None:
        if self._storage_info.is_up_to_date():
            return
        data = self._storage_info.load()
        self.is_started = data["isStarted"]
        self.last_successful_agreement = data["last_successful_agreement"]
        self.leaders = [UUID(identifier) for identifier in data["leaders"]]

    def all(self) -> list[UUID]:
        if not self._storage.is_up_to_date():
            self.refresh_list()
        return self.uuids

    def set(self, uuids: list[UUID]) -> None:
        self.uuids = uuids
        self._storage.dump(uuids)

    def set_info_data(self, is_started: bool, leaders: list[UUID]) -> None:
        self.refresh_info()
        self.is_started = is_started
        self.leaders = leaders
        self._storage_info.dump(self.prepare_info_data())

    def set_last_successful_agreement(self, last_successful_agreement: int):
        self.refresh_info()
        self.last_successful_agreement = last_successful_agreement
        self._storage_info.dump(self.prepare_info_data())

    def prepare_info_data(self) -> dict:
        return {
            "isStarted": self.is_started,
            "last_successful_agreement": self.last_successful_agreement,
            "leaders": [leader.hex for leader in self.leaders]
        }