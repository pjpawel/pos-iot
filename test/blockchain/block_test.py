from io import BytesIO
from time import time
from uuid import uuid4
from hashlib import sha256
from copy import copy
from pos.blockchain.transaction import Transaction
from pos.blockchain.block import Block


def test_encode_and_decode():
    uid = uuid4()
    signature = sha256(b'abc')
    tx = Transaction(1, int(time()), uid, signature.digest(), {"message": "abc", "id": 5})
    tx2 = copy(tx)
    tx2.signature = sha256(b'def').digest()
    tx2.data = {"message": "def", "id": 6}

    block = Block(
        2,
        int(time()),
        sha256(b'12345').digest(),
        uuid4(),
        sha256(b'asdfg').digest() * 8,
        [tx, tx2]
    )

    encoded_block = block.encode()

    b_io = BytesIO(encoded_block)
    block_new = Block.decode(b_io)
    assert block_new == block
