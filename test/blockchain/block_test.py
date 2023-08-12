from io import BytesIO
from time import time
from uuid import uuid4
from hashlib import sha256
from copy import copy

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pos.blockchain.transaction import Tx
from pos.blockchain.block import Block, BlockCandidate


def test_encode_and_decode():
    uid = uuid4()
    signature = sha256(b'abc')
    tx = Tx(1, int(time()), uid, signature.digest(), {"message": "abc", "id": 5})
    tx2 = copy(tx)
    tx2.signature = sha256(b'def').digest()
    tx2.data = {"message": "def", "id": 6}
    block_p = BlockCandidate(2, int(time()), None, None, [tx, tx2])

    private_key = Ed25519PrivateKey.generate()
    block = block_p.sign(sha256(b'12345').digest(), uuid4(), private_key)

    encoded_block = block.encode()

    b_io = BytesIO(encoded_block)
    block_new = Block.decode(b_io)
    assert block_new == block
