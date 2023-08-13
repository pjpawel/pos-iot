import base64
from copy import copy
from hashlib import sha256
from time import time
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pos.blockchain.block import Block, BlockCandidate
from pos.blockchain.blockchain import Blockchain, PoS, decode_chain
from pos.blockchain.node import SelfNode, NodeType
from pos.blockchain.transaction import Tx

from test.blockchain.conftest import Helper


def test_first_block_creation(helper: Helper):
    # TODO: move to block
    helper.put_storage_env()
    helper.put_node_type_env()
    helper.delete_storage_key()

    blockchain = Blockchain()
    self_node = SelfNode.load()

    blockchain.create_first_block(self_node)

    assert len(blockchain.blocks) == 1
    assert blockchain.blocks[0].verify(self_node.public_key)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    assert not blockchain.blocks[0].verify(public_key)


def test_pos_load(helper: Helper):
    """
    Test if PoS is correctly loaded genesis node
    :param helper:
    :return:
    """
    helper.put_genesis_node_env()
    pos = PoS()
    pos.load()

    assert isinstance(pos.self_node, SelfNode)
    assert len(pos.blockchain.blocks) == 1


def create_block() -> Block:
    uid = uuid4()
    signature = sha256(b'abc')
    tx = Tx(1, int(time()), uid, signature.digest(), {"message": "abc", "id": 5})
    tx2 = copy(tx)
    tx2.signature = sha256(b'def').digest()
    tx2.data = {"message": "def", "id": 6}
    block_p = BlockCandidate(2, int(time()), None, None, [tx, tx2])

    private_key = Ed25519PrivateKey.generate()
    return block_p.sign(sha256(b'12345').digest(), uuid4(), private_key)


def test_decode_blockchain():
    chain = []
    for i in range(6):
        chain.append(create_block())

    encoded = b''.join([block.encode() for block in chain])

    new_chain = decode_chain(encoded)

    assert len(chain) == len(new_chain)
    assert chain == new_chain


def test_node_register(helper: Helper):
    helper.put_genesis_node_env()
    pos = PoS()
    pos.load()

    ip = "192.168.1.200"
    port = 5000
    n_type = NodeType.VALIDATOR
    response = pos.node_register(ip, port, n_type)

    assert UUID(response.get("identifier"))
    assert response.get("host") == ip
    assert response.get("port") == 5000


def test_node_update(helper: Helper):
    helper.put_genesis_node_env()
    pos = PoS()
    pos.load()

    assert len(pos.blockchain.blocks) == 1

    response = pos.node_update({})

    blockchain_b64encoded = response.get("blockchain")
    nodes = response.get("nodes")

    blockchain_byt = base64.b64decode(bytes.fromhex(blockchain_b64encoded))

    chain = decode_chain(blockchain_byt)

    assert pos.blockchain.blocks == chain

    assert isinstance(nodes, list)

