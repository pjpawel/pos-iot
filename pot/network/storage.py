import csv
import json
import logging
import os
import time
import traceback
from io import BytesIO
from sys import getsizeof
from typing import BinaryIO
from uuid import UUID
from pathlib import Path

from pot.network.block import Block
from pot.network.node import Node
from pot.network.transaction import TxToVerify, Tx, TxVerified


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

    def __init__(self, storage: str | None = None):
        self._storage_dir = os.getenv("STORAGE_DIR") if not storage else storage
        self.path = os.path.join(self._storage_dir, self.PATH)
        self._lock = self.path + ".lock"
        Path(self.path).touch(0o777)
        self.invalidate_cache()  # TODO: Po nim nie może nastąpić is_up_to_date

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

    def unlock(self) -> None:
        if self._is_set_lock():
            os.remove(self._lock)

    def wait_for_set_lock(self, timeout: int = 10) -> None:
        while self._is_set_lock():
            time.sleep(0.001)
        self._set_lock()

    def _wait_for_lock(self) -> None:
        while self._is_set_lock():
            time.sleep(0.001)

    def invalidate_cache(self) -> None:
        self._cached_size = 0
        self._cached_mtime = 0


class BlocksStorage(Storage):
    PATH = 'blockchain'

    def load(self) -> list[Block]:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.update_cache()
            return []
        with open(self.path, "rb") as f:
            blocks = self.load_from_file(f)
        self.update_cache()
        return blocks

    def dump(self, blocks: list[Block]):
        self.wait_for_set_lock()
        logging.info(f"Writing {len(blocks)} {self.PATH} to storage")
        try:
            with open(self.path, 'wb') as f:
                f.write(encode_chain(blocks))
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e

    def update(self, blocks: list[Block]):
        self.wait_for_set_lock()
        logging.info(f"Appending {len(blocks)} {self.PATH} to storage")
        try:
            with open(self.path, 'ab') as f:
                f.write(encode_chain(blocks))
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e

    def load_from_file(self, f: BinaryIO) -> list[Block]:
        byt = f.read()
        if len(byt) == 0:
            return []
        return decode_chain(byt)


class NodeStorage(Storage):
    PATH = 'nodes'

    def load(self) -> list[Node]:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.update_cache()
            return []
        with open(self.path) as f:
            reader = csv.reader(f)
            nodes = [Node.load_from_list(data) for data in reader]
        self.update_cache()
        return nodes

    def dump(self, nodes: list[Node]) -> None:
        self.wait_for_set_lock()
        logging.info(f"Writing {len(nodes)} nodes to storage {self.PATH}")
        try:
            with open(self.path, 'w') as f:
                writer = csv.writer(f)
                writer.writerows([node.to_list() for node in nodes])
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e

    def update(self, nodes: list[Node]) -> None:
        self.wait_for_set_lock()
        logging.info(f"Appending {len(nodes)} nodes to storage {self.PATH}")
        try:
            with open(self.path, 'a') as f:
                writer = csv.writer(f)
                writer.writerows([node.to_list() for node in nodes])
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e


class NodeTrustStorage(Storage):
    PATH = 'nodes_trust'

    def load(self) -> dict[UUID, int]:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.update_cache()
            return {}
        with open(self.path, 'r') as f:
            reader = csv.reader(f)
            trusts = {}
            for row in reader:
                trusts[UUID(row[0])] = int(row[1])
        self.update_cache()
        return trusts

    def update(self, trusts: dict[UUID, int]) -> None:
        logging.info(f"Appending {len(trusts)} {self.PATH} to storage")
        self.wait_for_set_lock()
        try:
            with open(self.path, 'a') as f:
                writer = csv.writer(f)
                for key in list(trusts.keys()):
                    writer.writerow([key.hex, str(trusts[key])])
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e

    def dump(self, trusts: dict[UUID, int], lock: bool = True) -> None:
        if lock:
            self.wait_for_set_lock()
        logging.info(f"Writing {len(trusts)} {self.PATH} to storage")
        try:
            with open(self.path, 'w') as f:
                writer = csv.writer(f)
                for key in list(trusts.keys()):
                    writer.writerow([key.hex, str(trusts[key])])
            self.update_cache()
            if lock:
                self.unlock()
        except Exception as e:
            if lock:
                self.unlock()
            raise e


class TransactionStorage(Storage):
    PATH = 'transaction'

    def dump(self, txs: dict[UUID, TxToVerify], lock: bool = True) -> None:
        if lock:
            self.wait_for_set_lock()
        logging.info(f"Writing {len(txs)} '{self.PATH}' to storage")
        try:
            with open(self.path, 'w') as f:
                writer = csv.writer(f)
                for key in list(txs.keys()):
                    writer.writerow([key.hex, txs[key].__str__()])
            self.update_cache()
            if lock:
                self.unlock()
        except Exception as e:
            if lock:
                self.unlock()
            raise e

    def update(self, txs: dict[UUID, TxToVerify]) -> None:
        self.wait_for_set_lock()
        logging.info(f"Appending {len(txs)} {self.PATH} to storage")
        try:
            with open(self.path, 'a') as f:
                writer = csv.writer(f)
                for key in list(txs.keys()):
                    writer.writerow([key.hex, txs[key].__str__()])
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e

    def load(self) -> dict[UUID, TxToVerify]:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.update_cache()
            return {}
        with open(self.path, 'r') as f:
            reader = csv.reader(f)
            txs = {}
            for row in reader:
                txs[UUID(row[0])] = TxToVerify.from_str(row[1])
        self.update_cache()
        return txs


class TransactionVerifiedStorage(Storage):
    PATH = 'transaction_verified'

    def load(self) -> dict[UUID, TxVerified]:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.update_cache()
            return {}
        with open(self.path, 'r') as f:
            reader = csv.reader(f)
            txs = {}
            for row in reader:
                txs[UUID(row[0])] = TxVerified.from_str(row[1])
        self.update_cache()
        return txs

    def update(self, txs: dict[UUID, TxVerified]) -> None:
        logging.info(f"Appending {len(txs)} {self.PATH} to storage")
        self.wait_for_set_lock()
        try:
            with open(self.path, 'a') as f:
                writer = csv.writer(f)
                for key in list(txs.keys()):
                    writer.writerow([key.hex, txs[key].__str__()])
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e

    def dump(self, txs: dict[UUID, TxVerified], lock: bool = True) -> None:
        if lock:
            self.wait_for_set_lock()
        logging.info(f"Writing {len(txs)} '{self.PATH}' to storage")
        try:
            with open(self.path, 'w') as f:
                writer = csv.writer(f)
                for key in list(txs.keys()):
                    writer.writerow([key.hex, txs[key].__str__()])
            self.update_cache()
            if lock:
                self.unlock()
        except Exception as e:
            if lock:
                self.unlock()
            raise e


class ValidatorStorage(Storage):
    PATH = 'validators'
    SEPARATOR = ';'

    def load(self) -> list[UUID]:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.unlock()
            return []
        with open(self.path) as f:
            uuids = [UUID(hx) for hx in f.read().split(self.SEPARATOR)]
        self.unlock()
        return uuids

    def dump(self, uuids: list[UUID]) -> None:
        self.wait_for_set_lock()
        logging.info(f"Writing {len(uuids)} '{self.PATH}' to storage")
        try:
            with open(self.path, 'w') as f:
                f.write(self.SEPARATOR.join([uid.hex for uid in uuids]))
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e


class ValidatorAgreementStorage(ValidatorStorage):
    PATH = 'validators_agreement'


class ValidatorAgreementInfoStorage(Storage):
    PATH = 'validators_agreement_info'

    def load(self) -> dict:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.update_cache()
            return {}
        with open(self.path) as f:
            data = json.load(f)
        self.update_cache()
        return data

    def dump(self, data: dict) -> None:
        self.wait_for_set_lock()
        logging.info(f"Writing {str(data)} {self.PATH} to storage")
        try:
            with open(self.path, 'w') as f:
                json.dump(data, f)
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e


class ValidatorAgreementResultStorage(Storage):
    PATH = 'validator_agreement_result'

    def load(self) -> dict[UUID, bool]:
        self._wait_for_lock()
        logging.info(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        if self.is_empty():
            self.update_cache()
            return {}
        with open(self.path, 'r') as f:
            reader = csv.reader(f)
            txs = {}
            for row in reader:
                txs[UUID(row[0])] = bool(row[1])
        self.update_cache()
        return txs

    def update(self, results: dict[UUID, bool]) -> None:
        logging.info(f"Appending {len(results)} {self.PATH} to storage")
        self.wait_for_set_lock()
        try:
            with open(self.path, 'a') as f:
                writer = csv.writer(f)
                for key in list(results.keys()):
                    writer.writerow([key.hex, results[key].__str__()])
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e

    def dump(self, txs: dict[UUID, bool]) -> None:
        logging.info(f"Writing {len(txs)} '{self.PATH}' to storage")
        self.wait_for_set_lock()
        try:
            with open(self.path, 'w') as f:
                writer = csv.writer(f)
                for key in list(txs.keys()):
                    writer.writerow([key.hex, txs[key].__str__()])
            self.update_cache()
            self.unlock()
        except Exception as e:
            self.unlock()
            raise e
