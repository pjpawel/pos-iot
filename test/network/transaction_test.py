from io import BytesIO
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pot.network.node import Node, NodeType
from pot.network.transaction import Tx, TxCandidate, TxToVerify
from test.network.conftest import Helper


def test_encode_and_decode(helper: Helper):
    self_node_info = helper.get_self_node_info()

    tx_c = TxCandidate({"d": "abc", "t": "1"})
    tx = tx_c.sign(self_node_info)

    encoded_tx = tx.encode()

    b_io = BytesIO(encoded_tx)
    tx_new = Tx.decode(b_io)
    assert tx_new == tx


def test_create_from_candidate(helper: Helper):
    self_node_info = helper.get_self_node_info()

    tx_c = TxCandidate({"abc": 15})

    tx = tx_c.sign(self_node_info)

    assert isinstance(tx, Tx)
    assert tx_c.data == tx.data


def test_sign_verify_keys(helper: Helper):
    private_key = Ed25519PrivateKey.generate()
    data = b"0000000000"
    signed = private_key.sign(data)
    private_key.public_key().verify(signed, data)


def test_sign_verify(helper: Helper):
    self_node = helper.get_self_node()

    tx_c = TxCandidate({"d": "abc", "t": "1"})
    tx = tx_c.sign(self_node)

    tx.validate(self_node)


def test_sign_verify_data_float(helper: Helper):
    self_node = helper.get_self_node()

    tx_c = TxCandidate({"d": 67.6, "t": "1"})
    tx = tx_c.sign(self_node)

    tx.validate(self_node)


def test_sign_verify_data_int(helper: Helper):
    self_node = helper.get_self_node()

    tx_c = TxCandidate({"d": 57, "t": "1"})
    tx = tx_c.sign(self_node)

    tx.validate(self_node)


def test_tx_verification_result_positive(helper: Helper):
    self_node_info = helper.get_self_node_info()

    tx_c = TxCandidate({"d": "abc", "t": "1"})
    tx = tx_c.sign(self_node_info)

    tx_to_verify = TxToVerify(tx, helper.get_self_node())
    tx_to_verify.add_verification_result(Node(uuid4(), "abc", 5000), True)
    tx_to_verify.add_verification_result(Node(uuid4(), "def", 5000), True)
    tx_to_verify.add_verification_result(Node(uuid4(), "ghi", 5000), False)

    assert tx_to_verify.is_voting_positive()

    tx_to_verify.add_verification_result(Node(uuid4(), "jkl", 5000), False)

    assert tx_to_verify.is_voting_positive() is False

    tx_to_verify.add_verification_result(Node(uuid4(), "mno", 5000), False)

    assert tx_to_verify.is_voting_positive() is False


def test_tx_to_validate_str(helper: Helper):
    self_node_info = helper.get_self_node_info()

    tx_c = TxCandidate({"d": "abc", "t": "1"})
    tx = tx_c.sign(self_node_info)

    tx_to_verify = TxToVerify(tx, helper.get_self_node())

    encoded = tx_to_verify.__str__()
    assert encoded == str(tx_to_verify)


def test_tx_to_validate_encode(helper: Helper):
    self_node_info = helper.get_self_node_info()
    node = self_node_info.get_node()
    node.type = NodeType.SENSOR

    tx_c = TxCandidate({"d": "abc", "t": "1"})
    tx = tx_c.sign(self_node_info)

    tx_to_verify = TxToVerify(tx, node)

    encoded = str(tx_to_verify)
    assert tx_to_verify == TxToVerify.from_str(encoded)


def test_tx_to_validate_encode_with_voting(helper: Helper):
    self_node_info = helper.get_self_node_info()
    node = self_node_info.get_node()
    node.type = NodeType.SENSOR

    tx_c = TxCandidate({"d": "abc", "t": "1"})
    tx = tx_c.sign(self_node_info)

    tx_to_verify = TxToVerify(tx, node)
    tx_to_verify.add_verification_result(helper.create_node(), True)

    encoded = str(tx_to_verify)
    assert tx_to_verify == TxToVerify.from_str(encoded)

def test_tx_to_validate_encode_with_voting2(helper: Helper):
    self_node_info = helper.get_self_node_info()
    node = self_node_info.get_node()
    node.type = NodeType.SENSOR

    tx_c = TxCandidate({"d": "abc", "t": "1"})
    tx = tx_c.sign(self_node_info)
    tx_to_verify = TxToVerify(tx, node)

    node = helper.create_node()
    print(f"Created node: {node.identifier.hex}")
    tx_to_verify.add_verification_result(node, True)

    node = helper.create_node()
    print(f"Created node: {node.identifier.hex}")
    tx_to_verify.add_verification_result(node, False)

    assert tx_to_verify == TxToVerify.from_str(str(tx_to_verify))

