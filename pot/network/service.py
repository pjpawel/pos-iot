from uuid import UUID

from pot.network.manager import BlockchainManager, NodeManager, TransactionToVerifyManager, TransactionVerifiedManager, \
    ValidatorAgreement
from pot.network.node import Node as NodeDto
from pot.network.transaction import TxVerified


class Blockchain(BlockchainManager):
    txs_verified: TransactionVerifiedManager

    def __init__(self):
        super().__init__()
        self.txs_verified = TransactionVerifiedManager()

    def add_new_transaction(self, uuid: UUID, tx: TxVerified) -> None:
        self.txs_verified.add(uuid, tx)

    def create_block(self):
        # TODO:
        pass


class Node(NodeManager):
    validator_agreement: ValidatorAgreement

    def __init__(self):
        super().__init__()
        self.validator_agreement = ValidatorAgreement()

    def is_validator(self, node: NodeDto) -> bool:
        validators = self.get_validator_nodes()
        for validator in validators:
            if validator.identifier == node.identifier:
                return True
        return False

    def is_agreement_started(self) -> bool:
        self.validator_agreement.refresh_info()
        return self.validator_agreement.is_started

    def get_agreement_list(self) -> list[UUID]:
        self.validator_agreement.refresh_info()
        return self.validator_agreement.all()

    def set_agreement_list(self, uuids: list[UUID]):
        self.validator_agreement.set(uuids)

    def clear_agreement_list(self):
        self.validator_agreement.set([])

    def get_agreement_leader(self):
        self.validator_agreement.refresh_info()
        return self.validator_agreement.leaders[len(self.validator_agreement.leaders)-1]


class TransactionToVerify(TransactionToVerifyManager):
    pass
