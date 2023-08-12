"""
Pytest fixtures for pos.blockchain test module
"""
import os

import pytest

from pos.blockchain.node import SelfNode


class Helper:

    @staticmethod
    def get_storage_dir() -> str:
        return os.path.join("test", "../storage")

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


@pytest.fixture()
def helper():
    return Helper

