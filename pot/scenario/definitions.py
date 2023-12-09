import random
from time import sleep
from uuid import uuid4, UUID

import requests
import logging

from .utils import get_random_from_list, print_runtime_error
from ..network.blockchain import PoS
from ..network.node import SelfNode, Node
from ..network.transaction import TxCandidate, TxToVerify

LOG_PREFIX = 'SCENARIO: '


def none_sender(pos: PoS):
    return


@print_runtime_error
def instant_sender(pos: PoS):
    """
    :param pos:
    :return:
    """
    while True:
        sleep(5)
        if pos.nodes.len() == 0:
            continue
        logging.info(LOG_PREFIX + 'Available nodes to send to: ' +
                     ', '.join([node.identifier.hex for node in pos.nodes.all()]))
        node = get_random_from_list(pos.nodes.all())
        logging.info(LOG_PREFIX + f"Creating transaction to send")
        tx_can = TxCandidate({"t": "1", "d": random.randint(0, 546)})
        tx = tx_can.sign(pos.self_node)
        response = requests.post(f"http://{node.host}:{node.port}/transaction", tx.encode())
        if response.status_code == 200:
            assert isinstance(response.json(), dict)
            uuid = UUID(response.json().get("id"))
            pos.tx_to_verified.add(uuid, TxToVerify(tx, pos.self_node))
            logging.info(LOG_PREFIX + f"Transaction {uuid.hex} sent successfully")
        else:
            logging.error(LOG_PREFIX + f"Error while sending transaction. Error: {response.text}")


@print_runtime_error
def mad_sender(self_node: SelfNode, nodes: list[Node]):
    while True:
        sleep(5)
        node = get_random_from_list(nodes)
        requests.post(f"http://{node.host}:{node.port}/transaction", {
            # TODO: generate random data with signature of sender
        })


@print_runtime_error
def simple_sender(pos: PoS):
    send = True
    while send:
        sleep(5)
        if pos.nodes.len() == 0:
            continue
        logging.info(LOG_PREFIX + 'Available nodes to send to: ' +
                     ''.join([node.identifier.hex for node in pos.nodes.all()]))
        node = get_random_from_list(pos.nodes.all())
        logging.info(LOG_PREFIX + f"Creating transaction to send")
        tx_can = TxCandidate({"t": "1", "d": random.randint(0, 546)})
        tx = tx_can.sign(pos.self_node)
        response = requests.post(f"http://{node.host}:{node.port}/transaction", tx.encode())
        if response.status_code == 200:
            assert isinstance(response.json(), dict)
            uuid = UUID(response.json().get("id"))
            pos.tx_to_verified.add(uuid, TxToVerify(tx, pos.self_node))
            logging.info(LOG_PREFIX + f"Transaction {uuid.hex} sent successfully")
            send = False
        else:
            logging.error(LOG_PREFIX + f"Error while sending transaction. Error: {response.text}")
