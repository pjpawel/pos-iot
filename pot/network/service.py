from hashlib import sha256
from uuid import UUID

from pot.network.block import BlockCandidate, Block
from pot.network.manager import BlockchainManager, NodeManager, TransactionToVerifyManager, TransactionVerifiedManager, \
    ValidatorAgreement, ValidatorAgreementInfoManager, ValidatorAgreementResult, NodeTrust, ValidatorManager
from pot.network.node import Node as NodeDto, SelfNodeInfo, NodeType
from pot.network.transaction import TxVerified


class Blockchain(BlockchainManager):
    VERSION = 1
    txs_verified: TransactionVerifiedManager

    def __init__(self):
        super().__init__()
        self.txs_verified = TransactionVerifiedManager()

    def add_new_transaction(self, uuid: UUID, tx: TxVerified) -> None:
        self.txs_verified.add(uuid, tx)

    def create_block(self, self_node: SelfNodeInfo) -> Block:
        txs_verified = self.txs_verified.all()
        txs = [txs_verified.tx for txs_verified in txs_verified.values()]
        cblock = BlockCandidate.create_new(txs)
        self.txs_verified.delete(list(txs_verified.keys()))
        block = cblock.sign(
            self.get_last_block().hash(),
            self_node.identifier,
            self_node.private_key
        )
        self.add(block)
        return block

    def create_first_block(self, self_node: SelfNodeInfo) -> None:
        block = BlockCandidate.create_new([])
        self.add(block.sign(
            sha256(b'0000000000').digest(),
            self_node.identifier,
            self_node.private_key
        ))


class Node(NodeManager):
    validator_agreement: ValidatorAgreement
    validator_agreement_info: ValidatorAgreementInfoManager
    validator_agreement_result: ValidatorAgreementResult
    node_trust: NodeTrust
    validators: ValidatorManager

    def __init__(self):
        super().__init__()
        self.validator_agreement = ValidatorAgreement()
        self.validator_agreement_info = ValidatorAgreementInfoManager()
        self.validator_agreement_result = ValidatorAgreementResult()
        self.node_trust = NodeTrust()
        self.validators = ValidatorManager()

    def prepare_all_nodes_info(self) -> list[dict]:
        return self.prepare_nodes_info(self.all())

    def prepare_nodes_info(self, nodes: list[NodeDto]) -> list[dict]:
        self.validators.set_nodes_type(nodes)
        info = []
        for node in nodes:
            node_info = node.__dict__
            node_info["trust"] = self.node_trust.get_node_trust(node)
            info.append(node_info)
        return info

    def update_from_json(self, nodes_dict: list[dict]) -> None:
        nodes = []
        validators = []
        for node_dict in nodes_dict:
            node = NodeDto.load_from_dict(node_dict)
            if self.find_by_identifier(node.identifier) is not None:
                continue
            self.node_trust.add_new_node_trust(node, int(node_dict.get("trust")))
            if getattr(NodeType, node_dict.get("type").upper()) == NodeType.VALIDATOR:
                validators.append(node.identifier)
            nodes.append(node)
        self._nodes += nodes
        self._storage.dump(self._nodes)
        #self.validators.set_validators(validators)

    def get_validator_nodes(self) -> list[NodeDto]:
        nodes = self.all()
        validator_ids = self.validators.all()
        validators = []
        for node in nodes:
            if node.identifier in validator_ids:
                validators.append(node)
        return validators

    def count_validator_nodes(self) -> int:
        return len(self.validators.all())

    def is_validator(self, node: NodeDto) -> bool:
        return node.identifier in self.validators.all()
        # validators = self.get_validator_nodes()
        # for validator in validators:
        #     if validator.identifier == node.identifier:
        #         return True
        # return False

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
        nnodes = self.len()
        if nnodes < 2:
            return nnodes
        return max(2, min(int(nnodes/5), int(nnodes/2)))


class TransactionToVerify(TransactionToVerifyManager):
    # TODO: is done?
    pass
