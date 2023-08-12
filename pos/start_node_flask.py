import logging
import os
import socket
from io import BytesIO
from uuid import uuid4
from base64 import b64encode, b64decode

import requests
from dotenv import load_dotenv
from flask import Flask, request

from pos.blockchain.blockchain import Blockchain, PoS
from pos.blockchain.node import Node, SelfNode
from pos.blockchain.transaction import TxCandidate, Tx
from pos.utils import setup_logger
from pos.scenario import run_scenarios

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
# hostname = socket.gethostname()
# ip = socket.gethostbyname(hostname)
# genesis_ip = os.getenv("GENESIS_NODE")
#
# if ip == genesis_ip:
#     name = "genesis"
# else:
#     name = "node"
# print(f"=== Running as {name} ===")
#
# blockchain = Blockchain()
# if blockchain.has_storage_files():
#     print("Blockchain loading from storage")
#     blockchain.load_from_storage()
# elif ip != genesis_ip:
#     print("Blockchain loading from genesis")
#     blockchain.load_from_genesis_node(genesis_ip)
#     blockchain.nodes.append(Node("", genesis_ip, 5000))
#
# self_node = SelfNode.load()
# blockchain.exclude_self_node(ip)
#
# if ip != genesis_ip and not blockchain.chain:
#     blockchain.create_first_block(self_node)

hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)
genesis_ip = os.getenv("GENESIS_NODE")

pos = PoS()
pos.load()

blockchain = pos.blockchain
self_node = pos.self_node

"""
Run scenarios in background
"""
run_scenarios(os.getenv('POS_SCENARIOS'), blockchain.nodes)

"""
Run flask app
"""
app = Flask(__name__)

"""
=================== Info API ===================
"""


@app.get("/info")
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


@app.get("/blockchain")
def get_blockchain():
    """
    Show blockchain storage
    :return:
    """
    return blockchain.blocks_to_dict()


@app.get("/nodes")
def nodes():
    """
    Show nodes in network
    :return:
    """
    return {
        "nodes": blockchain.nodes_to_dict()
    }


@app.get("/public-key")
def get_public_key():
    """
    Get node public key
    :return:
    """
    return self_node.get_public_key_str()


"""
=================== Action API ===================
"""


@app.post("/transaction")
def add_transaction():
    """
    Add new transaction to block candidate
    :return:
    """
    try:
        pos.add_transaction(request.data)
    except Exception:
        return {"Invalid transaction data"}, 400


@app.post("/node/populate-new")
def populate_new_node():
    """
    Request must be in form: {
        "identifier": "<identifier>",
        "host": "<host>",
        "port": <port>
    }
    :return:
    """
    if request.remote_addr is not genesis_ip:
        return {"message": "Only genesis node can populate another node"}, 400
    pos.populate_new_node(request.get_json())


"""
=================== Genesis API ===================
"""


@app.post("/genesis/register")
def genesis_register():
    """
    Initialize node registration
    :return:
    """
    if ip != genesis_ip:
        return {"message": "Node is not genesis"}, 400
    return pos.genesis_register(request.remote_addr)


@app.post("/genesis/update")
def genesis_update():
    """
    Node identifier must be valid uuid hex
    :return:
    """
    if ip != genesis_ip:
        return {"message": "Node is not genesis"}, 400
    return pos.genesis_update(request.get_json())
