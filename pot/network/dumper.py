import logging
import os
from pathlib import Path
from time import time
from shutil import copy

from pot.network.blockchain import PoT


class Dumper:
    SECOND_PART = 10.0

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
        logging.debug(f"Dumping files to directory: {self.dump_dir}")

    def dump(self) -> None:
        utime = int(time() * self.SECOND_PART)
        # logging.debug(f"Dumping files with timestamp {utime}")
        dump_time_dir = os.path.join(self.dump_dir, str(utime))

        os.mkdir(dump_time_dir)

        for path in list(os.scandir(self.storage_dir)):
            if path.name.endswith(".lock"):
                continue
            copy(path, dump_time_dir)
            Path(os.path.join(dump_time_dir, path)).chmod(0o777)

        # for path in self.paths:
        #     copy(path, dump_time_dir)
