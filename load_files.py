from dotenv import load_dotenv

from pot.network.blockchain import PoT
from pot.utils import setup_logger

print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger("LOADING")

"""
Load/create files
"""
pot = PoT()
pot.load()
