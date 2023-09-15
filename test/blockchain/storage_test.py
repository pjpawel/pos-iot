import os

from pos.blockchain.storage import BlocksStorage
from test.blockchain.conftest import Helper


def test_blocks_storage_has_files(helper:Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    assert storage.has_files()

    if os.path.isfile(storage.path):
        os.remove(storage.path)

    assert storage.has_files() is False


def test_blocks_storage_dump(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    storage.dump([helper.create_block()])

    assert storage._cached_mtime != 0
    assert storage.is_up_to_date()

    os.remove(storage.path)


def test_blocks_storage_update_empty(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    storage.update([helper.create_block()])

    assert storage._cached_mtime != 0
    assert storage.is_up_to_date()

    os.remove(storage.path)


def test_blocks_storage_dump_many(helper: Helper):
    helper.put_storage_env()

    storage = BlocksStorage()

    storage.dump([helper.create_block(), helper.create_block()])

    assert storage._cached_mtime != 0
    assert storage.is_up_to_date()

    os.remove(storage.path)

