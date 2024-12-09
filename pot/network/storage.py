import csv
import json
import logging
import os
import time
import fcntl
from io import BytesIO
from typing import BinaryIO
from uuid import UUID
from pathlib import Path

from pot.network.block import Block
from pot.network.node import Node
from pot.network.transaction import TxToVerify, TxVerified
from .trust import NodeTrustChange


def encode_chain(blocks: list[Block]) -> bytes:
    return b"".join([block.encode() for block in blocks])


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
    PATH = ""
    path: str
    _storage_dir: str
    _lock: str
    _cached_mtime: float
    _cached_size: int

    def __init__(self, storage: str | None = None):
        self._storage_dir = os.getenv("STORAGE_DIR") if not storage else storage
        self.path = os.path.join(self._storage_dir, self.PATH)
        self._lock = self.path + ".lock"
        if not os.path.isfile(self.path):
            Path(self.path).touch(0o777)
        self.invalidate_cache()  # TODO: Po nim nie może nastąpić is_up_to_date

    def is_up_to_date(self):
        return self._cached_mtime == os.path.getmtime(
            self.path
        ) and self._cached_size == os.path.getsize(self.path)

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
    PATH = "blockchain"

    def load(self) -> list[Block]:
        # self._wait_for_lock()
        f = open(self.path, "rb")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            blocks = []
            if not self.is_empty():
                # with open(self.path, "rb") as f:
                blocks = self.load_from_file(f)
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return blocks

    def dump(self, blocks: list[Block]):
        f = open(self.path, "wb")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {len(blocks)} {self.PATH} to storage")
            f.write(encode_chain(blocks))
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def update(self, blocks: list[Block]):
        f = open(self.path, "ab")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Appending {len(blocks)} {self.PATH} to storage")
            f.write(encode_chain(blocks))
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def load_from_file(self, f: BinaryIO) -> list[Block]:
        byt = f.read()
        if len(byt) == 0:
            return []
        return decode_chain(byt)


class NodeStorage(Storage):
    PATH = "nodes"

    def load(self) -> list[Node]:
        f = open(self.path, "r")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            nodes = []
            if not self.is_empty():
                reader = csv.reader(f)
                nodes = [Node.load_from_list(data) for data in reader]
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return nodes

    def dump(self, nodes: list[Node]) -> None:
        f = open(self.path, "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {len(nodes)} {self.PATH} to storage")
            writer = csv.writer(f)
            writer.writerows([node.to_list() for node in nodes])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def update(self, nodes: list[Node]) -> None:
        f = open(self.path, "a")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Appending {len(nodes)} {self.PATH} to storage")
            writer = csv.writer(f)
            writer.writerows([node.to_list() for node in nodes])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class NodeTrustStorage(Storage):
    PATH = "nodes_trust"

    def load(self) -> dict[UUID, int]:
        f = open(self.path, "r")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            trusts = {}
            if not self.is_empty():
                reader = csv.reader(f)
                for row in reader:
                    trusts[UUID(row[0])] = int(row[1])
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return trusts

    def update(self, trusts: dict[UUID, int]) -> None:
        f = open(self.path, "a")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Appending {len(trusts)} {self.PATH} to storage")
            writer = csv.writer(f)
            for key in list(trusts.keys()):
                writer.writerow([key.hex, str(trusts[key])])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def dump(self, trusts: dict[UUID, int]) -> None:
        f = open(self.path, "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {len(trusts)} {self.PATH} to storage")
            writer = csv.writer(f)
            for key in list(trusts.keys()):
                writer.writerow([key.hex, str(trusts[key])])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class TransactionStorage(Storage):
    PATH = "transaction"

    def dump(self, txs: dict[UUID, TxToVerify], lock: bool = True) -> None:
        if lock:
            self.wait_for_set_lock()
        logging.debug(f"Writing {len(txs)} '{self.PATH}' to storage")
        try:
            with open(self.path, "w") as f:
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
        # TODO: change
        # f = open(self.path, 'w')
        # try:
        #     if lock:
        #         fcntl.flock(f, fcntl.LOCK_EX)
        #     logging.debug(f"Writing {len(txs)} {self.PATH} to storage")
        #     writer = csv.writer(f)
        #     for key in list(txs.keys()):
        #         writer.writerow([key.hex, txs[key].__str__()])
        #     f.flush()
        #     self.update_cache()
        # finally:
        #     if lock:
        #         fcntl.flock(f, fcntl.LOCK_UN)
        #     f.close()

    def update(self, txs: dict[UUID, TxToVerify]) -> None:
        self.wait_for_set_lock()
        logging.debug(f"Appending {len(txs)} {self.PATH} to storage")
        try:
            with open(self.path, "a") as f:
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
        logging.debug(f"Loading '{self.PATH}' from storage of size: {self.get_size()}")
        txs = {}
        if not self.is_empty():
            with open(self.path, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    txs[UUID(row[0])] = TxToVerify.from_str(row[1])
        self.update_cache()
        return txs


class TransactionVerifiedStorage(Storage):
    PATH = "transaction_verified"

    def load(self) -> dict[UUID, TxVerified]:
        f = open(self.path, "r")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            txs = {}
            if not self.is_empty():
                reader = csv.reader(f)
                for row in reader:
                    txs[UUID(row[0])] = TxVerified.from_str(row[1])
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return txs

    def update(self, txs: dict[UUID, TxVerified]) -> None:
        f = open(self.path, "a")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Appending {len(txs)} {self.PATH} to storage")
            writer = csv.writer(f)
            for key, value in txs.items():
                writer.writerow([key.hex, value.__str__()])
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def dump(self, txs: dict[UUID, TxVerified]) -> None:
        f = open(self.path, "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {len(txs)} '{self.PATH}' to storage")
            writer = csv.writer(f)
            for key, value in txs.items():
                writer.writerow([key.hex, value.__str__()])
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class ValidatorStorage(Storage):
    PATH = "validators"
    SEPARATOR = ";"

    def load(self) -> list[UUID]:
        f = open(self.path, "r")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            uuids = []
            if not self.is_empty():
                uuids = [UUID(hx) for hx in f.read().split(self.SEPARATOR)]
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return uuids

    def dump(self, uuids: list[UUID]) -> None:
        f = open(self.path, "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {len(uuids)} {self.PATH} to storage")
            f.write(self.SEPARATOR.join([uid.hex for uid in uuids]))
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class ValidatorAgreementStorage(ValidatorStorage):
    PATH = "validators_agreement"


class ValidatorAgreementInfoStorage(Storage):
    PATH = "validators_agreement_info"

    def load(self) -> dict:
        f = open(self.path, "r")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            data = {}
            if not self.is_empty():
                data = json.load(f)
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return data

    def dump(self, data: dict) -> None:
        f = open(self.path, "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {str(data)} {self.PATH} to storage")
            json.dump(data, f)
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class ValidatorAgreementResultStorage(Storage):
    PATH = "validator_agreement_result"

    def load(self) -> dict[UUID, bool]:
        f = open(self.path, "r")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            txs = {}
            if not self.is_empty():
                reader = csv.reader(f)
                for row in reader:
                    txs[UUID(row[0])] = bool(row[1])
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return txs

    def update(self, results: dict[UUID, bool]) -> None:
        f = open(self.path, "a")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Appending {len(results)} {self.PATH} to storage")
            writer = csv.writer(f)
            for key in list(results.keys()):
                writer.writerow([key.hex, results[key].__str__()])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def dump(self, txs: dict[UUID, bool]) -> None:
        f = open(self.path, "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {len(txs)} '{self.PATH}' to storage")
            writer = csv.writer(f)
            for key in list(txs.keys()):
                writer.writerow([key.hex, txs[key].__str__()])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class NodeTrustHistory(Storage):
    PATH = "node_trust_history"

    def load(self) -> list[NodeTrustChange]:
        f = open(self.path, "r")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(
                f"Loading '{self.PATH}' from storage of size: {self.get_size()}"
            )
            node_trusts = []
            if not self.is_empty():
                reader = csv.reader(f)
                node_trusts = [NodeTrustChange.load_from_list(data) for data in reader]
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        return node_trusts

    def dump(self, nodes_trusts: list[NodeTrustChange]) -> None:
        f = open(self.path, "w")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Writing {len(nodes_trusts)} '{self.PATH}' to storage")
            writer = csv.writer(f)
            writer.writerows([node_trust.to_list() for node_trust in nodes_trusts])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def update(self, node_trusts: list[NodeTrustChange]) -> None:
        f = open(self.path, "a")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Appending {len(node_trusts)} {self.PATH} to storage")
            writer = csv.writer(f)
            writer.writerows([node_trust.to_list() for node_trust in node_trusts])
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class NodeTrustFullHistory(NodeTrustHistory):
    PATH = "node_trust_full_history"

    def update(self, node_trusts: list[NodeTrustChange]) -> None:
        f = open(self.path, "a")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            logging.debug(f"Appending {len(node_trusts)} {self.PATH} to storage")
            writer = csv.writer(f)
            data = []
            timestamp = time.time()
            for node_trust in node_trusts:
                record = node_trust.to_list()
                record.append(timestamp)
                data.append(record)
            writer.writerows(data)
            f.flush()
            self.update_cache()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
