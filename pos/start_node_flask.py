import json
import logging
import os
import socket
from logging.handlers import TimedRotatingFileHandler
from copy import copy

import jsonpickle
import requests
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
from flask import Flask, request

from pos.blockchain.blockchain import Blockchain, Node, SelfNode
from pos.utils import setup_logger
from scenario import run_scenarios

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

if ip == genesis_ip:
    name = "genesis"
else:
    name = "node"
print(f"=== Running as {name} ===")

blockchain = Blockchain()
if blockchain.has_storage_files():
    print("Blockchain loading from storage")
    blockchain.load_from_storage()
elif ip != genesis_ip:
    print("Blockchain loading from genesis")
    blockchain.load_from_genesis_node(genesis_ip)
    # TODO: Identifier of genesis node
    blockchain.nodes.append(Node(genesis_ip, 5000))

self_node = SelfNode.load_self()
blockchain.exclude_self_node(ip)

"""
Run scenarios in Threads
"""
run_scenarios(os.getenv('POS_SCENARIOS'), blockchain.nodes)

"""
Run flask app
"""
app = Flask(__name__)


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
        "hostname": hostname
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
    return self_node.public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")


@app.post("/transaction")
def add_transaction():
    data = request.get_json()
    pass


@app.post("/node/populate-new")
def populate_new_node():
    """
    JSON: {
        "identifier": "<identifier>",
        "host": "<host>",
        "port": <port>
    }
    :return:
    """
    if request.remote_addr is not genesis_ip:
        return {"message": "Only genesis node can populate another node"}, 400
    data = request.get_json()
    identifier = data.get("identifier")
    host = data.get("host")
    port = int(data.get("port"))
    blockchain.nodes.append(Node(identifier, host, port))


@app.post("/genesis/update")
def genesis_update():
    if ip != genesis_ip:
        return {"message": "Node is not genesis"}, 400
    data = request.get_json()
    register_node = data.get("register", False)
    port = int(data.get("port", 5000))
    identifier = data.get("identifier")
    last_block_hash = data.get("lastBlock", None)

    blocks_to_show = None
    nodes_to_show = None

    if register_node:
        new_node = Node(identifier, request.remote_addr, port)
        data_to_send = {
            "host": new_node.host,
            "port": new_node.port
        }
        for node in blockchain.nodes:
            requests.post(f"http://{node.host}:{node.port}/node/populate-new", data_to_send)

        nodes_to_show = copy(blockchain.nodes)
        blockchain.nodes.append(new_node)
    elif last_block_hash is not None:

        for blocks in blockchain.chain:
            pass



    return json.dumps({
        "blockchain": [jsonpickle.encode(block) for block in blocks_to_show or blockchain.chain],
        "nodes": [jsonpickle.encode(node) for node in nodes_to_show or blockchain.nodes]
    })
