from io import BytesIO
from hashlib import sha256

from pos.network.transaction import TxCandidate
from pos.network.block import Block, BlockCandidate
from test.network.conftest import Helper


def test_encode_and_decode(helper: Helper):

    self_node = helper.get_self_node()

    tx_c = TxCandidate({"d": "abc", "t": "5"})
    tx = tx_c.sign(self_node)

    tx_c_2 = TxCandidate({"d": "def", "t": "0"})
    tx_2 = tx_c_2.sign(self_node)

    block_p = BlockCandidate.create_new([tx, tx_2])

    block = block_p.sign(sha256(b'12345').digest(), self_node.identifier, self_node.private_key)

    encoded_block = block.encode()

    b_io = BytesIO(encoded_block)
    block_new = Block.decode(b_io)

    assert block_new == block
