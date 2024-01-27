import logging
import os
from time import time
from shutil import copy

from pot.network.blockchain import PoT


class Dumper:
    dump_dir: str
    paths: list[str]
    storage_dir: str

    def __init__(self, pot: PoT):
        # self.paths = [
        #     pot.blockchain.get_storage().path,
        #     pot.nodes.get_storage().path,
        #     pot.tx_to_verified.get_storage().path
        # ]
        self.storage_dir = os.getenv("STORAGE_DIR")
        self.dump_dir = os.getenv("DUMP_DIR")
        if not os.path.isdir(self.dump_dir):
            os.mkdir(self.dump_dir)
        # self.dump_dir = os.path.join(base_dump_dir, str(int(time())))
        # if not os.path.isdir(self.dump_dir):
        #     os.mkdir(self.dump_dir)
        logging.info(f"Dumping files to directory: {self.dump_dir}")

    def dump(self) -> None:
        utime = int(time())
        # logging.info(f"Dumping files with timestamp {utime}")
        dump_time_dir = os.path.join(self.dump_dir, str(utime))

        os.mkdir(dump_time_dir)

        for path in list(os.scandir(self.storage_dir)):
            copy(path, dump_time_dir)

        # for path in self.paths:
        #     copy(path, dump_time_dir)
