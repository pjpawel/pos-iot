import socket
from os import getenv

from dotenv import load_dotenv
from network.peer import Peer
from blockchain.blockchain import Blockchain, BlockchainHandler


load_dotenv()

ip = (socket.gethostbyname(socket.gethostname()))

if ip is getenv("GENESIS_NODE"):
    blockchain = Blockchain
else:
    # call genesis and get blockchain

node = Peer("localhost", 5050)
node.start(BlockchainHandler())
