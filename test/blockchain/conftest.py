"""
Pytest fixtures for pos.blockchain test module
"""
import os
import socket
from hashlib import sha256

import pytest

from pos.blockchain.block import Block, BlockCandidate
from pos.blockchain.node import SelfNode, NodeType
from pos.blockchain.transaction import TxCandidate, Tx, TxToVerify


class Helper:

    @staticmethod
    def get_storage_dir() -> str:
        return os.path.relpath(os.path.join("test", "storage"))

    @staticmethod
    def get_storage_key_path() -> str:
        return os.path.join(Helper.get_storage_dir(), SelfNode.INFO_PATH)

    @staticmethod
    def delete_storage_key() -> None:
        key_path = Helper.get_storage_key_path()
        if os.path.isfile(key_path):
            os.remove(key_path)

    @staticmethod
    def clear_storage() -> None:
        Helper.put_storage_env()
        storage_dir = Helper.get_storage_dir()
        for file in os.listdir(storage_dir):
            if file == '.gitignore':
                continue
            os.remove(os.path.join(storage_dir, file))

    @staticmethod
    def put_storage_env() -> None:
        os.environ["STORAGE_DIR"] = Helper.get_storage_dir()

    @staticmethod
    def put_genesis_node_env(real_ip: bool = True) -> None:
        os.environ["GENESIS_NODE"] = socket.gethostbyname(socket.gethostname()) if real_ip else "localhost"

    @staticmethod
    def put_node_type_env(n_type: NodeType = NodeType.VALIDATOR) -> None:
        os.environ["NODE_TYPE"] = n_type.name

    @staticmethod
    def get_self_node(n_type=None) -> SelfNode:
        Helper.put_storage_env()
        Helper.delete_storage_key()
        return SelfNode.load(n_type)

    @staticmethod
    def create_block() -> Block:
        self_node = Helper.get_self_node()

        tx_c = TxCandidate({"message": "abc", "id": 5})
        tx = tx_c.sign(self_node)

        tx_c_2 = TxCandidate({"message": "def", "id": 6})
        tx_2 = tx_c_2.sign(self_node)

        block_p = BlockCandidate.create_new([tx, tx_2])

        return block_p.sign(sha256(b'12345').digest(), self_node.identifier, self_node.private_key)

    @staticmethod
    def create_transaction() -> Tx:
        self_node = Helper.get_self_node()
        tx_c = TxCandidate({"message": "abc", "id": 5})
        return tx_c.sign(self_node)

    @staticmethod
    def create_tx_to_verify() -> TxToVerify:
        return TxToVerify(Helper.create_transaction(), Helper.get_self_node())


@pytest.fixture()
def helper():
    return Helper


@pytest.fixture(autouse=True)
def around_test():
    Helper.clear_storage()
    yield
