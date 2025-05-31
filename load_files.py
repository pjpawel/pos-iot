from dotenv import load_dotenv

from post.network.blockchain import PoT
from post.utils import setup_logger

print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger("LOAD")

"""
Load/create files
"""
pot = PoT()
pot.load()
