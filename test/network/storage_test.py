import os
from copy import copy
from uuid import uuid4

from post.network.block import Block
from post.network.node import Node
from post.network.storage import BlocksStorage, TransactionStorage, NodeStorage
from test.network.conftest import Helper


def test_blocks_storage_has_files(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    assert storage.has_files()

    if os.path.isfile(storage.path):
        os.remove(storage.path)

    assert storage.has_files() is False


def test_blocks_storage_dump(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    storage.dump([helper.create_block()])

    assert storage._cached_mtime != 0
    assert storage.is_up_to_date()

    os.remove(storage.path)


def test_blocks_storage_update_empty(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    storage.update([helper.create_block()])

    assert storage._cached_mtime != 0
    assert storage.is_up_to_date()

    os.remove(storage.path)


def test_blocks_storage_dump_many(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    storage.dump([helper.create_block(), helper.create_block()])

    assert storage._cached_mtime != 0
    assert storage.is_up_to_date()


def test_blocks_load(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    blocks_dumping = [helper.create_block(), helper.create_block()]

    storage.dump(blocks_dumping)

    blocks = storage.load()

    assert blocks_dumping == blocks

    assert isinstance(blocks, list)
    assert len(blocks) == 2
    assert isinstance(blocks[0], Block)


def test_transaction_storage(helper: Helper):
    storage = TransactionStorage()

    mtime_old = copy(storage._cached_mtime)
    size_old = copy(storage._cached_size)

    uid = uuid4()
    storage.update({uid: helper.create_tx_to_verify()})

    assert not (mtime_old == storage._cached_mtime and size_old == storage._cached_size)
    assert storage.is_up_to_date()


def test_transaction(helper: Helper):
    storage = TransactionStorage()

    uid = uuid4()
    txs_updating = {uid: helper.create_tx_to_verify()}

    storage.update(txs_updating)

    txs = storage.load()

    assert len(txs) == len(txs_updating)
    tx = txs[uid]
    utx = txs_updating[uid]

    assert tx.voting == utx.voting
    assert tx.time == utx.time
    assert tx.tx == utx.tx
    # assert tx.node == utx.node
    assert txs == txs_updating


def test_transaction_adding_validator(helper: Helper):
    storage = TransactionStorage()

    uid = uuid4()
    txs = {uid: helper.create_tx_to_verify()}

    storage.update(txs)


def test_node(helper: Helper):
    storage = NodeStorage()

    uid = uuid4()
    node = Node(uid, "localhost", 5000)

    storage.update([node])

    assert os.path.getsize(storage.path) != 0
    assert storage.is_up_to_date()

    nodes = storage.load()

    assert len(nodes) == 1

    assert node == nodes[0]
