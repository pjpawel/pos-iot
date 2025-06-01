import random
from time import sleep
from uuid import UUID

import requests
import logging
import numpy as np

from .utils import get_random_from_list, print_runtime_error
from ..network.blockchain import PoST
from ..network.transaction import TxCandidate, TxToVerify

LOG_PREFIX = "SCENARIO: "


def none_sender(pot: PoST):
    return


@print_runtime_error
def instant_sender(pot: PoST):
    """
    :param pot:
    :return:
    """
    while True:
        sleep(10)
        if pot.nodes.len() == 0:
            continue
        logging.debug(
            LOG_PREFIX
            + "Available nodes to send to: "
            + ", ".join([node.identifier.hex for node in pot.nodes.all()])
        )
        if pot.nodes.count_validator_nodes() < 2:
            continue
        node = get_random_from_list(pot.nodes.get_validator_nodes())
        if node.identifier == pot.self_node.identifier:
            continue
        logging.debug(
            LOG_PREFIX + f"Creating transaction to send to node {node.identifier.hex}"
        )
        tx_can = TxCandidate({"t": "1", "d": random.randint(10, 15), "n": 0})
        tx = tx_can.sign(pot.self_node)
        response = requests.post(
            f"http://{node.host}:{node.port}/transaction", tx.encode()
        )
        if response.status_code == 200:
            assert isinstance(response.json(), dict)
            uuid = UUID(response.json().get("id"))
            self_node = pot.nodes.find_by_identifier(pot.self_node.identifier)
            if pot.nodes.is_validator(self_node):
                pot.tx_to_verified.add(uuid, TxToVerify(tx, self_node))
            logging.debug(LOG_PREFIX + f"Transaction {uuid.hex} sent successfully")
        else:
            logging.error(
                LOG_PREFIX
                + f"Error while sending transaction. Response: {response.text}. "
                f"Code: {response.status_code}"
            )


@print_runtime_error
def mad_sender(pot: PoST):
    def generate_unverifiable_number(history, k_factor=2.5):
        if len(history) < 2:
            return random.randint(0, 5)
        mean = np.mean(history)
        std = np.std(history)
        min_accepted = mean - std
        max_accepted = mean + std
        if np.random.rand() < 0.5:
            return min_accepted - k_factor * std
        else:
            return max_accepted + k_factor * std

    history = []
    while True:
        sleep(10)
        if pot.nodes.len() == 0:
            continue
        logging.debug(
            LOG_PREFIX
            + "Available nodes to send to: "
            + ", ".join([node.identifier.hex for node in pot.nodes.all()])
        )
        if pot.nodes.count_validator_nodes() < 2:
            continue
        node = get_random_from_list(pot.nodes.get_validator_nodes())
        if node.identifier == pot.self_node.identifier:
            continue
        logging.debug(
            LOG_PREFIX + f"Creating transaction to send to node {node.identifier.hex}"
        )
        value = generate_unverifiable_number(history)
        tx_can = TxCandidate({"t": "1", "d": value, "n": 0})
        tx = tx_can.sign(pot.self_node)
        response = requests.post(
            f"http://{node.host}:{node.port}/transaction", tx.encode()
        )
        if response.status_code == 200:
            assert isinstance(response.json(), dict)
            uuid = UUID(response.json().get("id"))
            self_node = pot.nodes.find_by_identifier(pot.self_node.identifier)
            if pot.nodes.is_validator(self_node):
                pot.tx_to_verified.add(uuid, TxToVerify(tx, self_node))
            logging.debug(LOG_PREFIX + f"Transaction {uuid.hex} sent successfully")
            history.append(value)
        else:
            logging.error(
                LOG_PREFIX
                + f"Error while sending transaction. Response: {response.text}. "
                  f"Code: {response.status_code}"
            )


@print_runtime_error
def simple_sender(pot: PoST):
    send = True
    while send:
        sleep(10)
        if pot.nodes.len() == 0:
            continue
        logging.debug(
            LOG_PREFIX
            + "Available nodes to send to: "
            + "".join([node.identifier.hex for node in pot.nodes.all()])
        )
        node = get_random_from_list(pot.nodes.get_validator_nodes())
        logging.debug(LOG_PREFIX + f"Creating transaction to send")
        tx_can = TxCandidate({"t": "1", "d": random.randint(10, 15)})
        tx = tx_can.sign(pot.self_node)
        response = requests.post(
            f"http://{node.host}:{node.port}/transaction", tx.encode()
        )
        if response.status_code == 200:
            assert isinstance(response.json(), dict)
            uuid = UUID(response.json().get("id"))
            self_node = pot.nodes.find_by_identifier(pot.self_node.identifier)
            if pot.nodes.is_validator(self_node):
                pot.tx_to_verified.add(uuid, TxToVerify(tx, self_node))
            logging.debug(LOG_PREFIX + f"Transaction {uuid.hex} sent successfully")
            send = False
        else:
            logging.error(
                LOG_PREFIX + f"Error while sending transaction. Error: {response.text}"
            )
