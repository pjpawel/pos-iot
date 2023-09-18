from uuid import uuid4

from pos.network.manager import TransactionToVerifyManager
from test.network.conftest import Helper


def test_transaction_verification(helper: Helper):
    manager = TransactionToVerifyManager()

    uid = uuid4()
    txs = helper.create_tx_to_verify()
    manager.add(uid, txs)

    manager.add_verification_result(uid, helper.get_self_node(), True) # NodeType.VALIDATOR

    txs = manager.find(uid)

    assert txs

    assert len(txs.voting) == 1

    manager.refresh()

    txs = manager.find(uid)

    assert txs

    assert len(txs.voting) == 1
