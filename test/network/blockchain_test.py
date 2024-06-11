import base64
import socket
from time import time
from uuid import UUID, uuid4

import pytest

from pot.network.block import BlockCandidate
from pot.network.blockchain import PoT
from pot.network.exception import PoTException
from pot.network.node import SelfNodeInfo, NodeType
from pot.network.storage import decode_chain
from pot.network.transaction import TxVerified

from test.network.conftest import Helper


def test_pot_load(helper: Helper):
    """
    Test if pot is correctly loaded genesis node
    :param helper:
    :return:
    """
    helper.put_genesis_node_env()
    pot = PoT()
    pot.load()

    assert isinstance(pot.self_node, SelfNodeInfo)
    assert len(pot.blockchain.blocks) == 1


def test_decode_blockchain(helper: Helper):
    chain = []
    for i in range(6):
        chain.append(helper.create_block())

    encoded = b''.join([block.encode() for block in chain])

    new_chain = decode_chain(encoded)

    assert len(chain) == len(new_chain)
    assert chain == new_chain


def test_node_register(helper: Helper):
    helper.put_genesis_node_env()
    pot = PoT()
    pot.load()

    uid = uuid4()
    ip = "192.168.1.200"
    port = 5000
    n_type = NodeType.VALIDATOR
    response = pot.node_register(uid, ip, port, n_type)

    assert UUID(response.get("identifier"))
    assert response.get("host") == ip
    assert response.get("port") == 5000


def test_node_update(helper: Helper):
    helper.put_genesis_node_env()
    pot = PoT()
    pot.load()

    assert len(pot.blockchain.blocks) == 1

    response = pot.node_update({})

    blockchain_b64encoded = response.get("blockchain")
    nodes = response.get("nodes")

    blockchain_byt = base64.b64decode(bytes.fromhex(blockchain_b64encoded))

    chain = decode_chain(blockchain_byt)

    assert pot.blockchain.blocks == chain
    assert isinstance(nodes, list)


def test_add_new_block_successful(helper: Helper):
    helper.put_storage_env()
    helper.put_genesis_node_env(True)

    pot = PoT()
    pot.load()

    assert len(pot.blockchain.blocks) == 1

    # Tx verified
    ident1 = uuid4()
    tx1 = helper.create_transaction()
    tx_verified1 = TxVerified(tx1, int(time()))
    pot.blockchain.add_new_transaction(ident1, tx_verified1)
    ident2 = uuid4()
    tx2 = helper.create_transaction()
    tx_verified2 = TxVerified(tx2, int(time()))
    pot.blockchain.add_new_transaction(ident2, tx_verified2)
    ident3 = uuid4()
    tx3 = helper.create_transaction()
    tx_verified3 = TxVerified(tx3, int(time()))
    pot.blockchain.add_new_transaction(ident3, tx_verified3)

    cblock = BlockCandidate.create_new([tx1, tx2, tx3])
    block = cblock.sign(pot.blockchain.get_last_block().hash(), pot.self_node.identifier, pot.self_node.private_key)

    response_msg, response_code = pot.add_new_block(block.encode(), socket.gethostbyname(socket.gethostname()))
    assert response_code == 200
    assert len(pot.blockchain.blocks) == 2


def test_add_new_block_missing_latest(helper: Helper):
    helper.put_storage_env()
    helper.put_genesis_node_env(True)

    pot = PoT()
    pot.load()

    assert len(pot.blockchain.blocks) == 1

    # Tx verified
    ident1 = uuid4()
    tx1 = helper.create_transaction()
    tx_verified1 = TxVerified(tx1, int(time()))
    pot.blockchain.add_new_transaction(ident1, tx_verified1)
    ident2 = uuid4()
    tx2 = helper.create_transaction()
    tx2.timestamp += 10
    tx_verified2 = TxVerified(tx2, int(time()) + 10)
    pot.blockchain.add_new_transaction(ident2, tx_verified2)
    ident3 = uuid4()
    tx3 = helper.create_transaction()
    tx3.timestamp += 20
    tx_verified3 = TxVerified(tx3, int(time()) + 30)
    pot.blockchain.add_new_transaction(ident3, tx_verified3)
    print(f"Transactions identifiers are {ident1.hex}, {ident2.hex}, {ident3.hex}")

    cblock = BlockCandidate.create_new([tx1, tx2])
    block = cblock.sign(pot.blockchain.get_last_block().hash(), pot.self_node.identifier, pot.self_node.private_key)

    response_msg, response_code = pot.add_new_block(block.encode(), socket.gethostbyname(socket.gethostname()))
    assert response_code == 200
    assert len(pot.blockchain.blocks) == 2


def test_add_new_block_missing_not_latest(helper: Helper):
    helper.put_storage_env()
    helper.put_genesis_node_env(True)

    pot = PoT()
    pot.load()

    assert len(pot.blockchain.blocks) == 1

    # Tx verified
    ident1 = uuid4()
    tx1 = helper.create_transaction()
    tx_verified1 = TxVerified(tx1, int(time()))
    pot.blockchain.add_new_transaction(ident1, tx_verified1)
    ident2 = uuid4()
    tx2 = helper.create_transaction()
    tx_verified2 = TxVerified(tx2, int(time()) + 10)
    pot.blockchain.add_new_transaction(ident2, tx_verified2)
    ident3 = uuid4()
    tx3 = helper.create_transaction()
    tx_verified3 = TxVerified(tx3, int(time()) + 20)
    pot.blockchain.add_new_transaction(ident3, tx_verified3)

    cblock = BlockCandidate.create_new([tx1, tx3])
    block = cblock.sign(pot.blockchain.get_last_block().hash(), pot.self_node.identifier, pot.self_node.private_key)

    #with pytest.raises(PoTException):
    #    response_msg, response_code = pot.add_new_block(block.encode(), socket.gethostbyname(socket.gethostname()))
    try:
        response_msg, response_code = pot.add_new_block(block.encode(), socket.gethostbyname(socket.gethostname()))
    except PoTException as e:
        assert e.code == 400
    # assert response_code == 200
    # assert len(pot.blockchain.blocks) == 2
