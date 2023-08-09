from io import BytesIO
from time import time
from uuid import uuid4
from hashlib import sha256
from pos.blockchain.transaction import Transaction


def test_encode_and_decode():
    uid = uuid4()
    signature = sha256(b'abc')
    tx = Transaction(1, int(time()), uid, signature.digest(), {"message": "abc", "id": 5})

    encoded_tx = tx.encode()

    # for byte in encoded_tx:
    #     print(byte, end=' ')
    # assert False

    b_io = BytesIO(encoded_tx)
    tx_new = Transaction.decode(b_io)
    assert tx_new == tx
