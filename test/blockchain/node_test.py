import os

from pos.blockchain.node import SelfNode

from test.blockchain.conftest import Helper


def test_load(helper: Helper):
    helper.put_storage_env()
    helper.delete_storage_key()

    node = SelfNode.load()
    assert os.path.isfile(helper.get_storage_key_path())

    node2 = SelfNode.load()
    assert node == node2




