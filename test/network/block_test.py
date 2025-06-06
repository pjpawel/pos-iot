from io import BytesIO
from hashlib import sha256
from time import time
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from post.network.node import SelfNodeInfo
from post.network.service import Blockchain
from post.network.transaction import TxCandidate, TxVerified
from post.network.block import Block, BlockCandidate
from test.network.conftest import Helper


def test_encode_and_decode(helper: Helper):

    self_node = helper.get_self_node_info()

    tx_c = TxCandidate({"d": "abc", "t": "5"})
    tx = tx_c.sign(self_node)

    tx_c_2 = TxCandidate({"d": "def", "t": "0"})
    tx_2 = tx_c_2.sign(self_node)

    block_p = BlockCandidate.create_new([tx, tx_2])

    block = block_p.sign(
        sha256(b"12345").digest(), self_node.identifier, self_node.private_key
    )

    encoded_block = block.encode()

    b_io = BytesIO(encoded_block)
    block_new = Block.decode(b_io)

    assert block_new == block


def test_first_block_creation(helper: Helper):
    helper.put_storage_env()
    helper.put_node_type_env()
    helper.delete_storage_key()

    blockchain = Blockchain()
    self_node = SelfNodeInfo()

    blockchain.create_first_block(self_node)

    assert len(blockchain.blocks) == 1
    assert blockchain.blocks[0].verify(self_node.public_key)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    assert not blockchain.blocks[0].verify(public_key)


def test_next_block_creation(helper: Helper):
    helper.put_storage_env()
    blockchain = Blockchain()
    self_node = SelfNodeInfo()

    blockchain.create_first_block(self_node)

    assert len(blockchain.all()) == 1

    ident = uuid4()
    tx_verified = TxVerified(helper.create_transaction(), int(time()))
    blockchain.add_new_transaction(ident, tx_verified)

    block = blockchain.create_block(self_node)

    assert len(blockchain.all()) == 2
    assert blockchain.all()[1] == block
    assert block.transactions[0] == tx_verified.tx


def test_next_block_creation_external(helper: Helper):
    helper.put_storage_env()
    blockchain = Blockchain()
    self_node = SelfNodeInfo()

    blockchain.create_first_block(self_node)

    assert len(blockchain.all()) == 1

    tx = helper.create_transaction()
    block = Block(
        1,
        int(time()),
        blockchain.get_last_block().hash(),
        self_node.identifier,
        sha256(b"1234567890").digest(),
        [tx],
    )
    blockchain.add(block)

    assert len(blockchain.all()) == 2
    assert blockchain.all()[1] == block
    assert block.transactions[0] == tx


def test_filter_last_transactions(helper: Helper):
    helper.put_storage_env()
    blockchain = Blockchain()
    self_node = SelfNodeInfo()

    blockchain.create_first_block(self_node)

    assert len(blockchain.all()) == 1

    def create_tx(tx_type: str):
        tx_c = TxCandidate({"d": "abc", "t": tx_type})
        tx_c.timestamp = int(time())
        return tx_c.sign(self_node)

    filter_type = "1"

    ident = uuid4()
    tx_verified = TxVerified(create_tx(filter_type), int(time()))
    blockchain.add_new_transaction(ident, tx_verified)

    last_txs = blockchain.find_last_transactions_values_for_node(
        self_node.get_node(), filter_type
    )
    assert len(last_txs) == 1
    assert last_txs[0]["type"] == filter_type
    assert last_txs[0]["data"] == tx_verified.tx.data

    last_txs = blockchain.find_last_transactions_values_for_node(
        self_node.get_node()
    )
    assert len(last_txs) == 1
    assert last_txs[0]["type"] == filter_type
    assert last_txs[0]["data"] == tx_verified.tx.data

    #create block
    blockchain.create_block(self_node)
    assert len(blockchain.txs_verified.all()) == 0

    last_txs = blockchain.find_last_transactions_values_for_node(
        self_node.get_node(), filter_type
    )
    assert len(last_txs) == 1
    assert last_txs[0]["type"] == filter_type
    assert last_txs[0]["data"] == tx_verified.tx.data





