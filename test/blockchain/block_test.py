from io import BytesIO
from hashlib import sha256

from pos.blockchain.transaction import TxCandidate
from pos.blockchain.block import Block, BlockCandidate
from test.blockchain.conftest import Helper


def test_encode_and_decode(helper: Helper):

    self_node = helper.get_self_node()

    tx_c = TxCandidate({"message": "abc", "id": 5})
    tx = tx_c.sign(self_node)

    tx_c_2 = TxCandidate({"message": "def", "id": 6})
    tx_2 = tx_c_2.sign(self_node)

    block_p = BlockCandidate.create_new([tx, tx_2])

    block = block_p.sign(sha256(b'12345').digest(), self_node.identifier, self_node.private_key)

    encoded_block = block.encode()

    b_io = BytesIO(encoded_block)
    block_new = Block.decode(b_io)

    assert block_new == block
