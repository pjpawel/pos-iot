import socket
import os
import sys

from dotenv import load_dotenv
from pos.network.peer import Peer
from pos.blockchain.blockchain import Blockchain, BlockchainHandler


def main(port: int = 5050):
    load_dotenv()

    ip = (socket.gethostbyname(socket.gethostname()))
    genesis_ip = os.getenv("GENESIS_NODE")

    blockchain = Blockchain()
    if blockchain.has_storage_files():
        blockchain.load_from_storage()
    elif ip is not genesis_ip:
        blockchain.load_from_genesis_node(genesis_ip)

    node = Peer("localhost", port)
    node.start(BlockchainHandler(blockchain))


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        main(int(sys.argv[1]))
    else:
        main()
