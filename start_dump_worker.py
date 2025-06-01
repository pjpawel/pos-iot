from time import sleep

from dotenv import load_dotenv

from post.network.blockchain import PoST
from post.network.dumper import Dumper
from post.utils import setup_logger, prepare_simulation_env


print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()
prepare_simulation_env()

"""
Configuring logger
"""
setup_logger("DUMP")

sleep(0.001)

pot = PoST()
pot.load(only_from_file=True)

dumper = Dumper(pot)
sleep_time = 1.0 / Dumper.SECOND_PART
while True:
    dumper.dump()
    sleep(sleep_time)
