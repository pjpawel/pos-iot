import logging
import os
import socket
from base64 import b64encode
from uuid import uuid4, UUID

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from pos.blockchain.blockchain import PoS, PoSException
from pos.blockchain.node import NodeType
from pos.utils import setup_logger

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger()

"""
Load blockchain
"""
hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)
genesis_ip = os.getenv("GENESIS_NODE")

pos = PoS()
pos.load()

blockchain = pos.blockchain
self_node = pos.self_node

"""
Run flask app
"""


app = Flask(__name__)


@app.errorhandler(PoSException)
def pos_error_handler(error: PoSException):
    return jsonify(error=error.message), error.code


"""
=================== Info API ===================
"""


@app.get("/info", endpoint='info')
def info():
    """
    Show info about node
    status: active/synchronizing/inactive
    ip: host ip
    :return:
    """
    return {
        "status": "active",
        "ip": ip,
        "hostname": hostname,
        "identifier": self_node.identifier.hex
    }


@app.get("/blockchain", endpoint='get_blockchain')
def get_blockchain():
    """
    Show blockchain storage
    :return:
    """
    return {"blockchain": blockchain.blocks_to_dict()}


@app.get("/blockchain/to-verify")
def get_transaction_to_verify():
    """
    :return:
    """
    data = {}
    for uuid, tx_to_verify in pos.tx_to_verified.all().items():
        data[uuid.hex] = {
            "timestamp": tx_to_verify.time,
            "transaction": b64encode(tx_to_verify.tx.encode()).hex(),
            "node": tx_to_verify.node.identifier.hex
        }
    return data


@app.get("/blockchain/verified")
def get_transaction_verified():
    """
    :return:
    """
    if not pos.blockchain.candidate:
        return {}
    return {
        "transactions": [{"timestamp": tx.timestamp, "data": tx.data} for tx in pos.blockchain.candidate.transactions]
    }


@app.get("/node/list")
def nodes():
    """
    Show nodes in network
    :return:
    """
    return {
        "nodes": pos.nodes.to_dict()
    }


@app.get("/public-key", endpoint='get_public_key')
def get_public_key():
    """
    Get node public key
    :return:
    """
    return self_node.get_public_key_str()


"""
=================== Action API ===================
"""


@app.post("/transaction", endpoint='new_transaction')
def transaction_new():
    """
    Add new transaction to block candidate
    :return:
    """
    try:
        # request.content_length
        # TODO: check content_length
        return pos.transaction_new(request.get_data(as_text=False), request.remote_addr)
    except Exception:
        logging.exception("Error registering new transaction")
        return "Invalid transaction data", 400


@app.post("/node/populate-new", endpoint='populate_node')
def populate_new_node():
    """
    Request must be in form: {
        "identifier": "<identifier>",
        "host": "<host>",
        "port": <port>
    }
    :return:
    """
    pos.populate_new_node(request.get_json(), request.remote_addr)


"""
=================== Validator API ===================
"""


@app.get("/transaction/<identifier>")
def transaction_get(identifier: str):
    return pos.transaction_get(identifier)


@app.post("/transaction/<identifier>/populate")
def transaction_populate(identifier: str):
    pos.transaction_populate(request.get_data(as_text=False), identifier)
    return {}


@app.post("/transaction/<identifier>/verifyResult")
def transaction_verify_result(identifier: str):
    request_json = request.get_json()
    pos.transaction_populate_verify_result(request_json.get("result"), identifier, request.remote_addr)
    return {}


@app.post("/node/register", endpoint='node_register')
def node_register():
    """
    Initialize node registration
    :return:
    """
    data = request.get_json()
    port = int(data.get("port"))
    n_type = getattr(NodeType, data.get("type"))
    identifier = UUID(data.get("identifier", uuid4().hex))
    return pos.node_register(identifier, request.remote_addr, port, n_type)


@app.post("/node/update", endpoint='node_update')
# @handle_pos_exception
def node_update():
    """
    Node identifier must be valid uuid hex
    :return:
    """
    return pos.node_update(request.get_json())


