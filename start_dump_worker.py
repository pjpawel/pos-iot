from time import sleep

from dotenv import load_dotenv

from pot.network.blockchain import PoS
from pot.network.dumper import Dumper
from pot.utils import setup_logger


print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger("DUMP")

sleep(0.001)

pos = PoS()
pos.load(only_from_file=True)

dumper = Dumper(pos)
while True:
    dumper.dump()
    sleep(1.0)







