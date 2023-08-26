from io import BytesIO
from uuid import uuid4

from pos.blockchain.node import Node
from pos.blockchain.transaction import Tx, TxCandidate, TxToVerify
from test.blockchain.conftest import Helper


def test_encode_and_decode(helper: Helper):
    self_node = helper.get_self_node()

    tx_c = TxCandidate({"message": "abc", "id": 5})
    tx = tx_c.sign(self_node)

    encoded_tx = tx.encode()

    b_io = BytesIO(encoded_tx)
    tx_new = Tx.decode(b_io)
    assert tx_new == tx


def test_create_from_candidate(helper: Helper):
    self_node = helper.get_self_node()

    tx_c = TxCandidate({"abc": 15})

    tx = tx_c.sign(self_node)

    assert isinstance(tx, Tx)
    assert tx_c.data == tx.data


def test_sign_verify(helper: Helper):
    self_node = helper.get_self_node()

    tx_c = TxCandidate({"message": "abc", "id": 5})
    tx = tx_c.sign(self_node)

    tx.validate(self_node)


def test_tx_verification_result_positive(helper: Helper):
    self_node = helper.get_self_node()

    tx_c = TxCandidate({"message": "abc", "id": 5})
    tx = tx_c.sign(self_node)

    tx_to_verify = TxToVerify(tx, self_node)
    tx_to_verify.add_verification_result(Node(uuid4(), "abc", 5000), True)
    tx_to_verify.add_verification_result(Node(uuid4(), "def", 5000), True)
    tx_to_verify.add_verification_result(Node(uuid4(), "ghi", 5000), False)

    assert tx_to_verify.is_voting_positive()

    tx_to_verify.add_verification_result(Node(uuid4(), "jkl", 5000), False)

    assert tx_to_verify.is_voting_positive() is False

    tx_to_verify.add_verification_result(Node(uuid4(), "mno", 5000), False)

    assert tx_to_verify.is_voting_positive() is False
