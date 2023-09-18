import base64
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pos.network.blockchain import PoS
from pos.network.service import Blockchain
from pos.network.node import SelfNode, NodeType
from pos.network.storage import decode_chain

from test.network.conftest import Helper


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
    pos = PoS()
    pos.load()

    uid = uuid4()
    ip = "192.168.1.200"
    port = 5000
    n_type = NodeType.VALIDATOR
    response = pos.node_register(uid, ip, port, n_type)

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
