from time import sleep

from dotenv import load_dotenv

from pot.network.blockchain import PoS
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
setup_logger()

sleep(10.0)

"""
Run verification of transactions
"""
pos = PoS()
pos.load(only_from_file=False)

tx_verifier = TransactionVerifier(pos)
tx_verifier.process()
