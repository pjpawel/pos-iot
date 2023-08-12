import os
import socket
from uuid import uuid4

import requests
from dotenv import load_dotenv
from flask import Flask, request

from pos.blockchain.blockchain import Blockchain
from pos.blockchain.node import Node, SelfNode
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
    # TODO: Identifier of genesis node from info
    blockchain.nodes.append(Node("", genesis_ip, 5000))

self_node = SelfNode.load()
blockchain.exclude_self_node(ip)

if ip != genesis_ip and not blockchain.chain:
    blockchain.create_first_block(self_node)

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
    TODO:
    :return:
    """
    data = request.get_json()
    pass


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
    data = request.get_json()
    identifier = data.get("identifier")
    host = data.get("host")
    port = int(data.get("port"))
    blockchain.nodes.append(Node(bytes.fromhex(identifier), host, port))


"""
=================== Genesis API ===================
"""


@app.post("/genesis/register")
def genesis_register():
    if ip != genesis_ip:
        return {"message": "Node is not genesis"}, 400
    identifier = uuid4()
    new_node = Node(identifier, request.remote_addr, 5000)
    data_to_send = {
        "identifier": identifier.bytes_le.hex(),
        "host": new_node.host,
        "port": new_node.port
    }
    for node in blockchain.nodes:
        requests.post(f"http://{node.host}:{node.port}/node/populate-new", data_to_send, timeout=15.0)
    blockchain.nodes.append(new_node)
    return data_to_send


@app.post("/genesis/update")
def genesis_update():
    """
    Node identifier must be valid uuid hex
    :return:
    """
    if ip != genesis_ip:
        return {"message": "Node is not genesis"}, 400
    data = request.get_json()
    last_block_hash = data.get("lastBlock", None)
    excluded_nodes = data.get("nodeIdentifiers", [])

    blocks_to_show = None
    nodes_to_show = None
    if last_block_hash is not None:
        # TODO: test this method
        blocks_to_show = []
        for block in blockchain.chain[::-1]:
            blocks_to_show.append(block)
            if block.prev_hash == last_block_hash:
                break
        blocks_to_show.reverse()
    if excluded_nodes:
        nodes_to_show = []
        for node in blockchain.nodes:
            if node.identifier.hex not in excluded_nodes:
                nodes_to_show.append(node)

    # TODO: maybe sent as encoded bytes
    return {
        "blockchain": [block.__dict__ for block in blocks_to_show or blockchain.chain],
        "nodes": [node.__dict__ for node in nodes_to_show or blockchain.nodes]
    }
