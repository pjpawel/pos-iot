from time import sleep

from dotenv import load_dotenv

from post.network.blockchain import PoT
from post.network.verifier import TransactionVerifier
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
setup_logger("VERIFY", "DEBUG")

sleep(10.0)

"""
Run verification of transactions
"""
pot = PoT()
pot.load(only_from_file=True)

tx_verifier = TransactionVerifier(pot)
tx_verifier.process()
