import os
from time import sleep

from dotenv import load_dotenv

from pos.blockchain.blockchain import PoS
from pos.scenario import run_scenarios
from pos.utils import setup_logger


print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger()

sleep(10.0)


"""
Run scenarios
"""
pos = PoS()
pos.load(only_from_file=False)

run_scenarios(os.getenv('POS_SCENARIOS'), pos)
