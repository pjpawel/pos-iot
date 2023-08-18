import logging
import os
import socket

from dotenv import load_dotenv
from flask import Flask, request

from pos.blockchain.blockchain import PoS, PoSException
from pos.blockchain.node import NodeType
from pos.utils import setup_logger
from pos.scenario import run_scenarios
from pos.blockchain.verifier import TransactionVerifier

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
Run verification of transactions in background
"""
tx_verifier = TransactionVerifier(pos)

"""
Run scenarios in background
"""
run_scenarios(os.getenv('POS_SCENARIOS'), pos.nodes)

"""
Run flask app
"""


def handle_pos_exception(func):
    def inner():
        try:
            return func()
        except PoSException as e:
            return e.message, e.code
    return inner


app = Flask(__name__)

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
    return blockchain.blocks_to_dict()


@app.get("/node/list")
def nodes():
    """
    Show nodes in network
    :return:
    """
    return {
        "nodes": [node.__dict__ for node in pos.nodes]
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
        return pos.transaction_new(request.data, request.remote_addr)
    except Exception as e:
        logging.warning(e)
        return {"Invalid transaction data"}, 400


@app.post("/node/populate-new", endpoint='populate_node')
@handle_pos_exception
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


@app.post("/node/register", endpoint='node_register')
@handle_pos_exception
def node_register():
    """
    Initialize node registration
    :return:
    """
    data = request.get_json()
    port = int(data.get("port"))
    n_type = getattr(NodeType, data.get("type"))
    return pos.node_register(request.remote_addr, port, n_type)


@app.post("/node/update", endpoint='node_update')
@handle_pos_exception
def node_update():
    """
    Node identifier must be valid uuid hex
    :return:
    """
    return pos.node_update(request.get_json())
