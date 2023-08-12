import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pos.blockchain.blockchain import Blockchain
from pos.blockchain.node import SelfNode


def delete_key_file(key_path: str) -> None:
    if os.path.isfile(key_path):
        os.remove(key_path)


def test_first_block_creation():
    # TODO: move to block
    storage_dir = os.path.join("test", "../storage")
    key_path = os.path.join(storage_dir, SelfNode.INFO_PATH)
    delete_key_file(key_path)
    os.environ["STORAGE_DIR"] = storage_dir

    blockchain = Blockchain()
    self_node = SelfNode.load()

    blockchain.create_first_block(self_node)

    assert len(blockchain.chain) == 1

    assert blockchain.chain[0].verify(self_node.public_key)

    delete_key_file(key_path)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    assert not blockchain.chain[0].verify(public_key)
