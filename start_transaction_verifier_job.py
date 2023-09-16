from time import sleep

from dotenv import load_dotenv

from pos.blockchain.blockchain import PoS
from pos.blockchain.verifier import TransactionVerifier
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
Run verification of transactions
"""
pos = PoS()
pos.load()

tx_verifier = TransactionVerifier(pos)
tx_verifier.start()
