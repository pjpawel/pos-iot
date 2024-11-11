import logging
import socket
import sys
from base64 import b64encode
from uuid import uuid4, UUID

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from pot.network.blockchain import PoT, PoTException
from pot.network.node import NodeType
from pot.utils import setup_logger

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
sys.argv[0] = "http"
setup_logger("API")

"""
Run flask app
"""
app = Flask(__name__)
"""
Load blockchain
"""
app.pot = PoT()
app.pot.load()


@app.errorhandler(PoTException)
def pot_error_handler(error: PoTException):
    logging.error(f"POT EXCEPTION: {error.message} - {error.code}")
    return jsonify(error=error.message), error.code


"""
=================== Info API ===================
"""


@app.get("/info", endpoint="info")
def info():
    """
    Show info about node
    status: active/synchronizing/inactive
    ip: host ip
    """
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return {
        "status": "active",
        "ip": ip,
        "hostname": hostname,
        "identifier": app.pot.self_node.identifier.hex,
    }


@app.get("/blockchain", endpoint="get_blockchain")
def get_blockchain():
    """
    Show blockchain storage
    :return:
    """
    return {"blockchain": app.pot.blockchain.blocks_to_dict()}


@app.get("/transaction/to-verify")
def get_transaction_to_verify():
    data = {}
    for uuid, tx_to_verify in app.pot.tx_to_verified.all().items():
        data[uuid.hex] = {
            "timestamp": tx_to_verify.time,
            "transaction": b64encode(tx_to_verify.tx.encode()).hex(),
            "node": tx_to_verify.node.identifier.hex,
            "voting": {
                "result": tx_to_verify.get_positive_votes(),
                "count": len(tx_to_verify.voting),
                "voting": [
                    {"uuid": k.hex, "result": v} for k, v in tx_to_verify.voting.items()
                ],
            },
        }
    return data


@app.get("/blockchain/verified")
def get_transaction_verified():
    return {
        "transactions": [
            {"identifier": uid.hex, "timestamp": tx.time, "data": tx.tx.data}
            for uid, tx in app.pot.blockchain.txs_verified.all().items()
        ]
    }


@app.get("/node/list")
def nodes():
    return {"nodes": app.pot.nodes.prepare_all_nodes_info()}


@app.get("/node/<identifier>")
def node(identifier: str):
    node_f = app.pot.nodes.find_by_identifier(UUID(identifier))
    if node_f is None:
        return "Node not found", 404
    return app.pot.nodes.prepare_nodes_info([node_f])[0]


@app.get("/public-key", endpoint="get_public_key")
def get_public_key():
    return app.pot.self_node.get_public_key_str()


"""
=================== Action API ===================
"""


@app.post("/transaction", endpoint="new_transaction")
def transaction_new():
    try:
        if request.content_length >= 1024:
            return "Transaction data is too long", 400
        return app.pot.transaction_new(
            request.get_data(as_text=False), request.remote_addr
        )
    except Exception:
        logging.exception("Error registering new transaction")
        return "Invalid transaction data", 400


@app.post(
    "/transaction/<identifier>/verified", endpoint="populate_transaction_verified"
)
def transaction_verified(identifier: str):
    try:
        if request.content_length >= 1024:
            return "Transaction data is too long", 400
        app.pot.transaction_verified_new(
            identifier, request.get_data(as_text=True), request.remote_addr
        )
        return ""
    except Exception:
        logging.exception("Error registering new transaction verified")
        return "Invalid transaction data", 400


@app.post("/block", endpoint="populate_block")
def block_new():
    try:
        app.pot.block_new(request.get_data(), request.remote_addr)
        return ""
    except Exception:
        logging.exception("Error registering new block")
        return "Invalid block data", 400


@app.post("/node/populate-new", endpoint="populate_node")
def populate_new_node():
    """
    Request must be in form: {
        "identifier": "<identifier>",
        "host": "<host>",
        "port": <port>
    }
    :return:
    """
    app.pot.populate_new_node(request.get_json(), request.remote_addr)
    return ""


@app.post("/blockchain/block/new", endpoint="blockchain_block_populate_node")
def populate_new_block():
    return app.pot.add_new_block(request.get_data(False), request.remote_addr)


@app.post("/node/validator/new", endpoint="inform_about_new_validator")
def new_validators():
    app.pot.node_new_validators(request.remote_addr, request.get_json())
    return ""


# CHECK
@app.patch("/node/<identifier>/trust", endpoint="node_trust_change")
def node_trust_change(identifier: str):
    app.pot.node_trust_change(identifier, request.get_json())
    return ""


"""
=================== Validator API ===================
"""


@app.get("/transaction/<identifier>")
def transaction_get(identifier: str):
    # TODO: nie jest VALIDATOR
    return app.pot.transaction_get(identifier)


@app.post("/transaction/<identifier>/populate")
def transaction_populate(identifier: str):
    # TODO: nie jest VALIDATOR
    app.pot.transaction_populate(request.get_data(as_text=False), identifier)
    return ""


@app.post("/transaction/<identifier>/verifyResult")
def transaction_verify_result(identifier: str):
    request_json = request.get_json()
    app.pot.transaction_populate_verify_result(
        request_json.get("result"), identifier, request.remote_addr
    )
    return ""


@app.post("/node/register", endpoint="node_register")
def node_register():
    """
    Initialize node registration
    :return:
    """
    data = request.get_json()
    port = int(data.get("port"))
    n_type = getattr(NodeType, data.get("type"))
    identifier = UUID(data.get("identifier", uuid4().hex))
    return app.pot.node_register(identifier, request.remote_addr, port, n_type)


@app.get("/node/update", endpoint="node_update")
def node_update():
    """
    Node identifier must be valid uuid hex
    :return:
    """
    return app.pot.node_update(request.args)


@app.post("/node/validator/agreement")
def validator_agreement_start():
    return app.pot.node_validator_agreement_start(
        request.remote_addr, request.get_json()
    )


@app.get("/node/validator/agreement")
def validator_agreement_get():
    return app.pot.node_validator_agreement_get(request.remote_addr)


@app.patch("/node/validator/agreement/vote")
def validator_agreement_vote():
    logging.warning(f"Agreement vote called")
    app.pot.node_validator_agreement_vote(request.remote_addr, request.get_json())
    return {}


@app.post("/node/validator/agreement/done")
def validator_agreement_done():
    logging.warning(f"Agreement done called")
    app.pot.node_validator_agreement_done(request.remote_addr, request.get_json())
    return {}
