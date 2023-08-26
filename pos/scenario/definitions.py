from time import sleep
from uuid import uuid4, UUID

import requests
import logging

from .utils import get_random_from_list, print_runtime_error
from ..blockchain.blockchain import PoS
from ..blockchain.node import SelfNode, Node
from ..blockchain.transaction import TxCandidate, TxToVerify

LOG_PREFIX = 'SCENARIO: '


def none_sender(pos: PoS):
    return


@print_runtime_error
def instant_sender(pos: PoS):
    """
    :param pos:
    :return:
    """
    sleep(15)
    # loop = True
    # while loop:
    sleep(5)
    if not pos.nodes:
        return
    #    continue
    logging.info(LOG_PREFIX + 'Available nodes to send to: ' + ''.join([node.identifier.hex for node in pos.nodes]))
    node = get_random_from_list(pos.nodes)
    tx_can = TxCandidate({"message": "abc", "id": uuid4().hex})
    tx = tx_can.sign(pos.self_node)
    response = requests.post(f"http://{node.host}:{node.port}/transaction", tx.encode())
    if response.status_code == 200:
        assert isinstance(response.json(), dict)
        uuid = UUID(response.json().get("id"))
        pos.tx_to_verified[uuid] = TxToVerify(tx, pos.self_node)
    else:
        logging.error(LOG_PREFIX + f"Error while sending transaction. Error: {response.text}")

    #loop = False


@print_runtime_error
def mad_sender(self_node: SelfNode, nodes: list[Node]):
    while True:
        sleep(5)
        node = get_random_from_list(nodes)
        requests.post(f"http://{node.host}:{node.port}/transaction", {
            # TODO: generate random data with signature of sender
        })


@print_runtime_error
def simple_sender(self_node: SelfNode, nodes: list[Node]):
    while True:
        sleep(5)
        node = get_random_from_list(nodes)
        requests.post(f"http://{node.host}:{node.port}/transaction", {
            # TODO: send the same data with signature of sender
        })
