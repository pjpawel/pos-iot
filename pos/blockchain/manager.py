from hashlib import sha256
from uuid import UUID

from .block import Block, BlockCandidate
from .node import SelfNode, Node, NodeType
from .storage import BlocksStorage, NodeStorage, TransactionStorage, Storage
from .transaction import Tx, TxToVerify


class Manager:
    _storage: Storage

    def has_storage_files(self) -> bool:
        return self._storage.has_files()

    def has_empty_files(self) -> bool:
        return self._storage.is_empty()


class Blockchain(Manager):
    _storage: BlocksStorage
    blocks: list[Block]
    candidate: BlockCandidate | None = None

    def __init__(self):
        self.blocks = []
        self._storage = BlocksStorage()

    def add_new_transaction(self, tx: Tx) -> None:
        if not self.candidate:
            self.candidate = BlockCandidate.create_new([])
        self.candidate.transactions.append(tx)

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
        return self._txs.get(identifier)

    def find(self, identifier: UUID) -> TxToVerify | None:
        return self._txs.get(identifier)

    def all(self) -> dict[UUID, TxToVerify]:
        return self._txs

    def pop(self, identifier: UUID) -> TxToVerify:
        return self._txs.pop(identifier)


class NodeManager(Manager):
    _nodes: list[Node]
    _storage: NodeStorage

    def __init__(self):
        self._nodes = []
        self._storage = NodeStorage()

    def to_dict(self) -> list[dict]:
        return [node.__dict__ for node in self._nodes]

    def add(self, node: Node) -> None:
        if not self._storage.is_up_to_date():
            self.refresh()
        self._nodes.append(node)
        self._storage.update([node])

    def all(self) -> list[Node]:
        return self._nodes

    def len(self) -> int:
        return len(self._nodes)

    def find_by_identifier(self, identifier: UUID) -> Node | None:
        for node in self._nodes:
            if node.identifier == identifier:
                return node
        return None

    def find_by_request_addr(self, request_addr: str) -> Node | None:
        for node in self._nodes:
            if node.host == request_addr:
                return node
        return None

    def update_from_json(self, nodes_dict: list[dict]) -> None:
        self._nodes = [Node.load_from_dict(data) for data in nodes_dict]

    def get_validator_nodes(self) -> list[Node]:
        validators = []
        for node in self._nodes:
            if node.type == NodeType.VALIDATOR:
                validators.append(node)
        return validators

    def refresh(self) -> None:
        self._nodes = [] if self._storage.is_empty() else self._storage.load()

    def count_validator_nodes(self, self_node: SelfNode) -> int:
        count = 0
        for node in self._nodes:
            if node.type == NodeType.VALIDATOR:
                count += 1
        if self_node.type == NodeType.VALIDATOR:
            count += 1
        return count

    def exclude_self_node(self, self_ip: str) -> None:
        for node in self._nodes:
            if node.host == self_ip:
                self._nodes.remove(node)
                return
