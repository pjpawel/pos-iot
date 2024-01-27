from time import sleep

from dotenv import load_dotenv

from pot.network.blockchain import PoT
from pot.network.verifier import TransactionVerifier
from pot.utils import setup_logger


print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger("VERIFY")

sleep(10.0)

"""
Run verification of transactions
"""
pot = PoT()
pot.load(only_from_file=True)

tx_verifier = TransactionVerifier(pot)
tx_verifier.process()
