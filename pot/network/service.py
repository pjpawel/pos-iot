from uuid import UUID

from pot.network.manager import BlockchainManager, NodeManager, TransactionToVerifyManager, TransactionVerifiedManager, \
    ValidatorAgreement, ValidatorAgreementInfoManager, ValidatorAgreementResult, NodeTrust
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
        # TODO: is necessary?
        pass


class Node(NodeManager):
    validator_agreement: ValidatorAgreement
    validator_agreement_info: ValidatorAgreementInfoManager
    validator_agreement_result: ValidatorAgreementResult
    node_trust: NodeTrust

    def __init__(self):
        super().__init__()
        self.validator_agreement = ValidatorAgreement()
        self.validator_agreement_info = ValidatorAgreementInfoManager()
        self.validator_agreement_result = ValidatorAgreementResult()
        self.node_trust = NodeTrust()

    def is_validator(self, node: NodeDto) -> bool:
        validators = self.get_validator_nodes()
        for validator in validators:
            if validator.identifier == node.identifier:
                return True
        return False

    def get_most_trusted_validator(self) -> NodeDto:
        trusts = {}
        validators = self.get_validator_nodes()
        for validator in validators:
            trusts[self.node_trust.get_node_trust(validator)] = validator

        sorted_trust = sorted(trusts, reverse=True)
        return trusts[sorted_trust[0]]

    def is_agreement_started(self) -> bool:
        self.validator_agreement_info.refresh()
        return self.validator_agreement_info.is_started

    def get_agreement_list(self) -> list[UUID]:
        self.validator_agreement.refresh()
        return self.validator_agreement.all()

    def set_agreement_list(self, uuids: list[UUID]):
        self.validator_agreement.set(uuids)

    def clear_agreement_list(self):
        self.validator_agreement.set([])

    def get_agreement_leader(self):
        self.validator_agreement_info.refresh()
        return self.validator_agreement_info.leaders[len(self.validator_agreement_info.leaders)-1]

    def is_agreement_voting_ended(self):
        # TODO: to be completed
        pass

    def is_agreement_result_success(self) -> bool:
        self.validator_agreement_result.refresh()
        n_success = sum(i is True for i in self.validator_agreement_result.all().values())
        validators_number = self.get_actual_validators_number()
        return n_success >= validators_number/2

    def get_actual_validators_number(self) -> int:
        return len(self.get_validator_nodes())

    def calculate_validators_number(self) -> int:
        return min(30, len(self.all()))


class TransactionToVerify(TransactionToVerifyManager):
    # TODO: is done
    pass
