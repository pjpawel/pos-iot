from time import time
from uuid import uuid4

from post.network.manager import (
    TransactionToVerifyManager,
    BlockchainManager,
    TransactionVerifiedManager,
)
from post.network.node import NodeType
from post.network.transaction import TxVerified
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


def test_verified_transaction_sorting(helper: Helper):
    helper.put_storage_env()
    manager = TransactionVerifiedManager()

    tx_verified100 = TxVerified(helper.create_transaction(10), 100)
    tx_verified500 = TxVerified(helper.create_transaction(50), 500)
    tx_verified300 = TxVerified(helper.create_transaction(30), 300)
    tx_verified200 = TxVerified(helper.create_transaction(20), 200)
    txs = [tx_verified100, tx_verified500, tx_verified300, tx_verified200]

    for tx in txs:
        manager.add(uuid4(), tx)

    assert len(manager.all()) == 4
    sorted = manager.sort_tx_by_time(manager.all())

    assert list(sorted.values()) == [
        tx_verified500,
        tx_verified300,
        tx_verified200,
        tx_verified100,
    ]


def test_verified_transaction_sorting_2(helper: Helper):
    helper.put_storage_env()
    manager = TransactionVerifiedManager()

    ident1 = uuid4()
    tx1 = helper.create_transaction()
    tx_verified1 = TxVerified(tx1, int(time()))

    ident2 = uuid4()
    tx2 = helper.create_transaction()
    tx2.timestamp += 10
    tx_verified2 = TxVerified(tx2, int(time()) + 10)

    ident3 = uuid4()
    tx3 = helper.create_transaction()
    tx3.timestamp += 20
    tx_verified3 = TxVerified(tx3, int(time()) + 30)

    txs = [tx_verified1, tx_verified2, tx_verified3]
    for tx in txs:
        manager.add(uuid4(), tx)

    assert len(manager.all()) == 3
    sorted = manager.sort_tx_by_time(manager.all())

    assert list(sorted.values()) == [tx_verified3, tx_verified2, tx_verified1]
