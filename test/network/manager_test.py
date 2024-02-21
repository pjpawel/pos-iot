from uuid import uuid4

from pot.network.manager import TransactionToVerifyManager
from pot.network.node import NodeType
from test.network.conftest import Helper


def test_transaction_verification(helper: Helper):
    manager = TransactionToVerifyManager()

    uid = uuid4()
    txs = helper.create_tx_to_verify()
    manager.add(uid, txs)

    manager.add_verification_result(uid, helper.get_self_node(NodeType.VALIDATOR), True)

    txs = manager.find(uid)

    assert txs

    assert len(txs.voting) == 1

    manager.refresh()

    txs = manager.find(uid)

    assert txs

    assert len(txs.voting) == 1
