import os

from pos.blockchain.node import SelfNode


def delete_key_file(key_path: str) -> None:
    if os.path.isfile(key_path):
        os.remove(key_path)


def test_load():
    storage_dir = os.path.join("test", "../storage")
    key_path = os.path.join(storage_dir, SelfNode.INFO_PATH)
    delete_key_file(key_path)
    os.environ["STORAGE_DIR"] = storage_dir

    node = SelfNode.load()
    assert os.path.isfile(key_path)

    node2 = SelfNode.load()
    assert node == node2

    delete_key_file(key_path)




