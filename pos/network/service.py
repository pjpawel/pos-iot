from uuid import UUID

from pos.network.block import BlockCandidate
from pos.network.manager import BlockchainManager, NodeManager, TransactionToVerifyManager, TransactionVerifiedManager
from pos.network.transaction import TxVerified


class Blockchain(BlockchainManager):
    txs_verified: TransactionVerifiedManager

    def __init__(self):
        super().__init__()
        self.txs_verified = TransactionVerifiedManager()

    def add_new_transaction(self, uuid: UUID, tx: TxVerified) -> None:
        self.txs_verified.add(uuid, tx)

    def create_block(self):
        pass


class Node(NodeManager):
    pass


class TransactionToVerify(TransactionToVerifyManager):
    pass

