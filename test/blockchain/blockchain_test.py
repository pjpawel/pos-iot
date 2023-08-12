from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pos.blockchain.blockchain import Blockchain
from pos.blockchain.node import SelfNode

from test.blockchain.conftest import Helper


def test_first_block_creation(helper: Helper):
    # TODO: move to block
    helper.put_storage_env()
    helper.delete_storage_key()

    blockchain = Blockchain()
    self_node = SelfNode.load()

    blockchain.create_first_block(self_node)

    assert len(blockchain.chain) == 1
    assert blockchain.chain[0].verify(self_node.public_key)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    assert not blockchain.chain[0].verify(public_key)
