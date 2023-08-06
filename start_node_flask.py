import json

import jsonpickle
from flask import Flask, request
import socket
import os
import requests

from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from blockchain.blockchain import Blockchain, BlockchainHandler, Node, SelfNode
from scenario import run_scenarios

load_dotenv()

hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)
genesis_ip = os.getenv("GENESIS_NODE")

if ip == genesis_ip:
    print("=== Running as genesis ===")
else:
    print("=== Running as node ===")

blockchain = Blockchain()
if blockchain.has_storage_files():
    print("Blockchain loading from storage")
    blockchain.load_from_storage()
elif ip != genesis_ip:
    print("Blockchain loading from genesis")
    blockchain.load_from_genesis_node(genesis_ip)

# TODO: It is necessary to store localhost node?

run_scenarios(os.getenv('POS_SCENARIOS'), blockchain.nodes)

self_node = SelfNode.load_self()

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
        "hostname": hostname,
        "genesisIp": genesis_ip
    }


@app.get("/blockchain")
def get_blockchain():
    """
    Show blockchain storage
    :return:
    """
    return {
        "blockchain": blockchain.chain
    }


@app.get("/nodes")
def nodes():
    """
    Show nodes in network
    :return:
    """
    return {
        "nodes": blockchain.nodes
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
    if request.remote_addr is not genesis_ip:
        return {"message": "Only genesis node can populate another node"}, 400
    data = request.get_json()
    host = data["host"]
    port = int(data['port'])
    blockchain.nodes.append(Node(host, port))


@app.post("/genesis/register_node")
def genesis_register_node():
    if ip != genesis_ip:
        return {"message": "Node is not genesis"}, 400
    data = request.get_json()
    port = int(data['port'])
    new_node = Node(request.remote_addr, port)
    data_to_send = {
        "host": new_node.host,
        "port": new_node.port
    }
    for node in blockchain.nodes:
        requests.post(f"http://{node.host}:{node.port}/node/populate-new", data_to_send)

    nodes_to_show = blockchain.nodes
    blockchain.nodes.append(new_node)

    return json.dumps({
        "blockchain": [jsonpickle.encode(block) for block in blockchain.chain],
        "nodes": [jsonpickle.encode(node) for node in nodes_to_show]
    })
