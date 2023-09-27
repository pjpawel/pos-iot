import logging
import os
from time import time
from shutil import copy

from pos.network.blockchain import PoS


class Dumper:
    dump_dir: str
    paths: list[str]

    def __init__(self, pos: PoS):
        self.paths = [
            pos.blockchain.get_storage().path,
            pos.nodes.get_storage().path,
            pos.tx_to_verified.get_storage().path
        ]
        self.dump_dir = os.getenv("DUMP_DIR")
        if not os.path.isdir(self.dump_dir):
            os.mkdir(self.dump_dir)

    def dump(self) -> None:
        utime = int(time())
        logging.info(f"Dumping files with timestamp {utime}")
        dump_time_dir = os.path.join(self.dump_dir, str(utime))

        os.mkdir(dump_time_dir)

        for path in self.paths:
            copy(path, dump_time_dir)
