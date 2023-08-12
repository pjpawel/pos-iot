from io import BytesIO
from time import time
from uuid import uuid4
from hashlib import sha256

from pos.blockchain.node import SelfNode
from pos.blockchain.transaction import Tx, TxCandidate
from test.blockchain.conftest import Helper


def test_encode_and_decode():
    uid = uuid4()
    signature = sha256(b'abc')
    tx = Tx(1, int(time()), uid, signature.digest(), {"message": "abc", "id": 5})

    encoded_tx = tx.encode()

    # for byte in encoded_tx:
    #     print(byte, end=' ')
    # assert False

    b_io = BytesIO(encoded_tx)
    tx_new = Tx.decode(b_io)
    assert tx_new == tx


def test_create_from_candidate(helper: Helper):
    helper.put_storage_env()
    helper.delete_storage_key()

    tx_c = TxCandidate({"abc": 15})
    self_node = SelfNode.load()
    tx = tx_c.sign(self_node)

    assert isinstance(tx, Tx)
    assert tx_c.data == tx.data
