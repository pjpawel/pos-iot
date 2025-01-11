import os
from time import sleep

from dotenv import load_dotenv

from pot.network.blockchain import PoT
from pot.scenario import run_scenarios
from pot.utils import setup_logger, prepare_simulation_env

print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()
prepare_simulation_env()

"""
Configuring logger
"""
setup_logger("SCENARIO")

sleep(10.0)

"""
Run scenarios
"""
pot = PoT()
pot.load(only_from_file=True)

run_scenarios(os.getenv("POT_SCENARIOS"), pot)
