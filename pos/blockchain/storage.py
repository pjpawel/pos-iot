import csv
import logging
import os
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
    _cached_mtime: float

    def __init__(self):
        self._storage_dir = os.getenv("STORAGE_DIR")
        self.path = os.path.join(self._storage_dir, self.PATH)
        Path(self.path).touch(0o777)
        self.update_cache_mtime()

    def is_up_to_date(self):
        return self._cached_mtime == os.path.getmtime(self.path)

    def update_cache_mtime(self):
        self._cached_mtime = os.path.getmtime(self.path)

    def has_files(self) -> bool:
        return os.path.isfile(self.path)

    def is_empty(self) -> bool:
        return os.path.getsize(self.path) == 0

    def get_size(self) -> int:
        return os.path.getsize(self.path)


class BlocksStorage(Storage):
    PATH = 'blockchain'

    def load(self) -> list[Block]:
        logging.info(f"Loading {self.PATH} from storage of size: {self.get_size()}")
        with open(self.path, "rb") as f:
            blocks = self.load_from_file(f)
        self.update_cache_mtime()
        return blocks

    def dump(self, blocks: list[Block]):
        logging.info(f"Writing {len(blocks)} {self.PATH} to storage")
        with open(self.path, 'wb') as f:
            f.write(encode_chain(blocks))
        self.update_cache_mtime()

    def update(self, blocks: list[Block]):
        logging.info(f"Appending {len(blocks)} {self.PATH} to storage")
        with open(self.path, 'ab') as f:
            f.write(encode_chain(blocks))
        self.update_cache_mtime()

    def load_from_file(self, f: BinaryIO) -> list[Block]:
        return decode_chain(f.read(getsizeof(f)))

    def load_from_bytes(self, b: bytes) -> list[Block]:
        return decode_chain(b)


class NodeStorage(Storage):
    PATH = 'nodes'

    def load(self) -> list[Node]:
        logging.info(f"Loading {self.PATH} from storage of size: {self.get_size()}")
        with open(self.path) as f:
            reader = csv.reader(f)
            nodes = [Node.load_from_list(data) for data in reader]
        self.update_cache_mtime()
        return nodes

    def dump(self, nodes: list[Node]) -> None:
        logging.info(f"Writing {len(nodes)} {self.PATH} to storage")
        with open(self.path, 'w') as f:
            writer = csv.writer(f)
            writer.writerows([node.to_list() for node in nodes])
        self.update_cache_mtime()

    def update(self, nodes: list[Node]) -> None:
        logging.info(f"Appending {len(nodes)} {self.PATH} to storage")
        with open(self.path, 'a') as f:
            writer = csv.writer(f)
            writer.writerows([node.to_list() for node in nodes])
        self.update_cache_mtime()


class TransactionStorage(Storage):
    PATH = 'transaction'

    def dump(self, txs: dict[UUID, TxToVerify]) -> None:
        logging.info(f"Writing {len(txs)} {self.PATH} to storage")
        with open(self.path, 'w') as f:
            writer = csv.writer(f)
            for key in list(txs.keys()):
                writer.writerow([key.hex, txs[key].__str__()])
        self.update_cache_mtime()

    def update(self, txs: dict[UUID, TxToVerify]) -> None:
        logging.info(f"Appending {len(txs)} {self.PATH} to storage")
        with open(self.path, 'a') as f:
            writer = csv.writer(f)
            for key in list(txs.keys()):
                writer.writerow([key.hex, txs[key].__str__()])
        self.update_cache_mtime()

    def load(self) -> dict[UUID, TxToVerify]:
        logging.info(f"Loading {self.PATH} from storage of size: {self.get_size()}")
        with open(self.path, 'r') as f:
            reader = csv.reader(f)
            txs = {}
            for row in reader:
                txs[UUID(row[0])] = TxToVerify.from_str(row[1])
        self.update_cache_mtime()
        return txs

