import csv
import logging
import os
import time
from io import BytesIO
from sys import getsizeof
from typing import BinaryIO
from uuid import UUID
from pathlib import Path

from pos.blockchain.block import Block
from pos.blockchain.node import Node
from pos.blockchain.transaction import TxToVerify


def encode_chain(blocks: list[Block]) -> bytes:
    return b''.join([block.encode() for block in blocks])


def decode_chain(byt: bytes) -> list[Block]:
    b = BytesIO(byt)
    end = len(byt)
    blocks = []
    while True:
        blocks.append(Block.decode(b))
        if end - b.tell() == 0:
            break
    return blocks


class Storage:
    PATH = ''
    path: str
    _storage_dir: str
    _lock: str
    _cached_mtime: float
    _cached_size: int

    def __init__(self):
        self._storage_dir = os.getenv("STORAGE_DIR")
        self.path = os.path.join(self._storage_dir, self.PATH)
        self._lock = self.path + ".lock"
        Path(self.path).touch(0o777)
        self.update_cache()

    def is_up_to_date(self):
        return self._cached_mtime == os.path.getmtime(self.path) and self._cached_size == os.path.getsize(self.path)

    def update_cache(self):
        self._cached_mtime = os.path.getmtime(self.path)
        self._cached_size = os.path.getsize(self.path)

    def has_files(self) -> bool:
        return os.path.isfile(self.path)

    def is_empty(self) -> bool:
        return os.path.getsize(self.path) == 0

    def get_size(self) -> int:
        return os.path.getsize(self.path)

    def _is_set_lock(self) -> bool:
        return os.path.isfile(self._lock)

    def _set_lock(self) -> None:
        Path(self._lock).touch(0o777)

    def _unlock(self) -> None:
        os.remove(self._lock)

    def _wait_for_set_lock(self, timeout: int = 10) -> None:
        while self._is_set_lock():
            time.sleep(0.001)
        self._set_lock()

    def _wait_for_lock(self) -> None:
        while self._is_set_lock():
            time.sleep(0.001)


class BlocksStorage(Storage):
    PATH = 'blockchain'

    def load(self) -> list[Block]:
        self._wait_for_lock()
        logging.info(f"Loading {self.PATH} from storage of size: {self.get_size()}")
        with open(self.path, "rb") as f:
            blocks = self.load_from_file(f)
        self.update_cache()
        return blocks

    def dump(self, blocks: list[Block]):
        self._wait_for_set_lock()
        logging.info(f"Writing {len(blocks)} {self.PATH} to storage")
        try:
            with open(self.path, 'wb') as f:
                f.write(encode_chain(blocks))
            self.update_cache()
            self._unlock()
        except Exception as e:
            self._unlock()
            raise e

    def update(self, blocks: list[Block]):
        self._wait_for_set_lock()
        logging.info(f"Appending {len(blocks)} {self.PATH} to storage")
        try:
            with open(self.path, 'ab') as f:
                f.write(encode_chain(blocks))
            self.update_cache()
            self._unlock()
        except Exception as e:
            self._unlock()
            raise e

    def load_from_file(self, f: BinaryIO) -> list[Block]:
        return decode_chain(f.read(getsizeof(f)))

    def load_from_bytes(self, b: bytes) -> list[Block]:
        return decode_chain(b)


class NodeStorage(Storage):
    PATH = 'nodes'

    def load(self) -> list[Node]:
        self._wait_for_lock()
        logging.info(f"Loading {self.PATH} from storage of size: {self.get_size()}")
        with open(self.path) as f:
            reader = csv.reader(f)
            nodes = [Node.load_from_list(data) for data in reader]
        self.update_cache()
        return nodes

    def dump(self, nodes: list[Node]) -> None:
        self._wait_for_set_lock()
        logging.info(f"Writing {len(nodes)} {self.PATH} to storage")
        try:
            with open(self.path, 'w') as f:
                writer = csv.writer(f)
                writer.writerows([node.to_list() for node in nodes])
            self.update_cache()
            self._unlock()
        except Exception as e:
            self._unlock()
            raise e

    def update(self, nodes: list[Node]) -> None:
        self._wait_for_set_lock()
        logging.info(f"Appending {len(nodes)} {self.PATH} to storage")
        try:
            with open(self.path, 'a') as f:
                writer = csv.writer(f)
                writer.writerows([node.to_list() for node in nodes])
            self.update_cache()
            self._unlock()
        except Exception as e:
            self._unlock()
            raise e


class TransactionStorage(Storage):
    PATH = 'transaction'

    def dump(self, txs: dict[UUID, TxToVerify]) -> None:
        self._wait_for_set_lock()
        logging.info(f"Writing {len(txs)} {self.PATH} to storage")
        try:
            with open(self.path, 'w') as f:
                writer = csv.writer(f)
                for key in list(txs.keys()):
                    writer.writerow([key.hex, txs[key].__str__()])
            self.update_cache()
            self._unlock()
        except Exception as e:
            self._unlock()
            raise e

    def update(self, txs: dict[UUID, TxToVerify]) -> None:
        self._wait_for_set_lock()
        logging.info(f"Appending {len(txs)} {self.PATH} to storage")
        try:
            with open(self.path, 'a') as f:
                writer = csv.writer(f)
                for key in list(txs.keys()):
                    writer.writerow([key.hex, txs[key].__str__()])
            self.update_cache()
            self._unlock()
        except Exception as e:
            self._unlock()
            raise e

    def load(self) -> dict[UUID, TxToVerify]:
        self._wait_for_lock()
        logging.info(f"Loading {self.PATH} from storage of size: {self.get_size()}")
        with open(self.path, 'r') as f:
            reader = csv.reader(f)
            txs = {}
            for row in reader:
                txs[UUID(row[0])] = TxToVerify.from_str(row[1])
        self.update_cache()
        return txs

