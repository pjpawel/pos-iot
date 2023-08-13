"""
Pytest fixtures for pos.blockchain test module
"""
import os
import socket

import pytest

from pos.blockchain.node import SelfNode, NodeType


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
    def put_storage_env() -> None:
        os.environ["STORAGE_DIR"] = Helper.get_storage_dir()

    @staticmethod
    def put_genesis_node_env(real_ip: bool = True) -> None:
        os.environ["GENESIS_NODE"] = socket.gethostbyname(socket.gethostname()) if real_ip else "localhost"

    @staticmethod
    def put_node_type_env(n_type: NodeType = NodeType.VALIDATOR) -> None:
        os.environ["NODE_TYPE"] = n_type.name

@pytest.fixture()
def helper():
    return Helper
