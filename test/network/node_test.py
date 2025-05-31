import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from post.network.node import SelfNodeInfo

from test.network.conftest import Helper


def encode_private_key(private_key: Ed25519PrivateKey):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def test_load(helper: Helper):
    helper.put_storage_env()
    helper.delete_storage_key()

    node = SelfNodeInfo()
    assert os.path.isfile(helper.get_storage_key_path())

    node2 = SelfNodeInfo()

    assert node.identifier == node2.identifier
    assert node.get_public_key_str() == node2.get_public_key_str()
    assert encode_private_key(node.private_key) == encode_private_key(node2.private_key)
