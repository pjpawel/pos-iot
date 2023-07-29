from .block import Block
from network.peer import Handler


class Blockchain:
    chain: list[Block]

    def __init__(self):
        self.chain = []

    def add_block(self, block: Block) -> None:
        self.chain.append(block)


class BlockchainHandler(Handler):

    def handle(self, data: str):
        print("=========")
        print("Data received")
        print(data)
        print("=========")
