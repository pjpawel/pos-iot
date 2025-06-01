import logging
import os
from pathlib import Path
from time import time
from shutil import copy

from post.network.blockchain import PoST


class Dumper:
    SECOND_PART = 10.0

    dump_dir: str
    paths: list[str]
    storage_dir: str

    def __init__(self, pot: PoST):
        self.storage_dir = os.getenv("STORAGE_DIR")
        self.dump_dir = os.getenv("DUMP_DIR")
        if not os.path.isdir(self.dump_dir):
            os.mkdir(self.dump_dir)
        logging.debug(f"Dumping files to directory: {self.dump_dir}")

    def dump(self) -> None:
        utime = int(time() * self.SECOND_PART)
        dump_time_dir = os.path.join(self.dump_dir, str(utime))

        os.mkdir(dump_time_dir)

        for path in list(os.scandir(self.storage_dir)):
            if path.name.endswith(".lock"):
                continue
            copy(path, dump_time_dir)
            Path(os.path.join(dump_time_dir, path)).chmod(0o777)

        # for path in self.paths:
        #     copy(path, dump_time_dir)
