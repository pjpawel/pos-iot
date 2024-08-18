import logging
import random
from threading import Thread
from time import sleep, time
from math import ceil
from random import randint

from dotenv import load_dotenv

from pot.network.blockchain import PoT
from pot.network.node import Node
from pot.network.request import Request
from pot.utils import setup_logger

print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger("AGREEMENT_VALIDATE", "DEBUG")

sleep(10)

pot = PoT()
pot.load(only_from_file=True)

node = pot.self_node.get_node()


def add_agreement_result(result: bool):
    pot.nodes.validator_agreement_result.add(node.identifier, result)
    vote_data = {
        "result": result
    }

    logging.debug(f"Validators list that is judged: {', '.join([vid.hex for vid in pot.nodes.validator_agreement.all()])}")

    def send(func):
        threads = []
        for node in pot.nodes.all():
            if node.identifier == pot.self_node.identifier or node.identifier not in pot.nodes.validators.all():
                continue
            logging.info(f"Sending validator agreement vote/done to host: {node.host}:{node.port} - starting thread")
            th = Thread(target=func, args=[node])
            th.start()
            threads.append(th)

        # Wait for all to end
        while True:
            if len(threads) != 0:
                break
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)

    def vote(node: Node):
        Request.send_validator_agreement_vote(node.host, node.port, vote_data)

    send(vote)

    # sleep(0.1)

    # if not pot.nodes.is_agreement_voting_ended() and pot.nodes.get_agreement_leader() != node.identifier:
    #     return
    #
    # logging.info("Ending validator agreement")
    #
    # new_leader = pot.nodes.get_most_trusted_validator()
    # new_validators = pot.nodes.validator_agreement.all()
    # logging.info(f"New validators: {', '.join([vid.hex for vid in new_validators])}")
    #
    # pot.nodes.clear_agreement_list()
    # if pot.nodes.is_agreement_result_success():
    #     pot.nodes.validators.set_validators(new_validators)
    #     pot.nodes.validator_agreement_info.set_last_successful_agreement(int(time()))
    #     pot.nodes.validator_agreement_info.set_info_data(False, [])
    # else:
    #     pot.nodes.validator_agreement_info.add_leader(new_leader)
    #
    # done_data = {
    #     "validators": [vid.hex for vid in pot.nodes.validator_agreement.all()],
    #     "leader": new_leader.identifier.hex
    # }
    #
    # def done(node: Node):
    #     Request.send_validator_agreement_done(node.host, node.port, done_data)
    #
    # send(done)
    #
    # pot.send_validators_list()

import socket
logging.info(f"Node: {node.identifier}. Socket: {socket.gethostbyname(socket.gethostname())}")

while True:

    if not pot.nodes.is_validator(node):
        sleep(10)
        continue

    logging.info(f"Checking if validator has work to do: {node.identifier.hex}")
    agreement_info = pot.nodes.validator_agreement_info
    agreement_info.refresh()
    if agreement_info.is_started:
        if pot.nodes.validator_agreement_result.find(node.identifier) is None:
            # TODO: check if agreement is working
            add_agreement_result(True)
            continue

            proposed_agreement_list = pot.nodes.validator_agreement_info.leaders

            if len(proposed_agreement_list) != len(set(proposed_agreement_list)):
                logging.warning(f"There are duplicates in agreement list")
                add_agreement_result(False)
                continue

            nodes = pot.nodes.prepare_all_nodes_info()
            nodes = sorted(nodes, key=lambda node_info: node_info["trust"])
            validator_len = max(2, ceil(len(nodes) * 0.1))
            proposed_agreement_list_len = len(proposed_agreement_list)
            if validator_len != proposed_agreement_list_len:
                logging.warning(
                    f"Calculated length of nodes ({validator_len}) is not equal agreement list ({proposed_agreement_list_len})")
                add_agreement_result(False)
                continue

            half_validator_len = int(validator_len / 2)
            agreement_list = nodes[0:half_validator_len]
            agreement_id_list = [node["identifier"] for node in agreement_list]

            # [validator.hex for validator in proposed_agreement_list[:proposed_agreement_list_len]]
            if proposed_agreement_list[:proposed_agreement_list_len] != agreement_id_list:
                diff = set(proposed_agreement_list[:proposed_agreement_list_len]).difference(set(agreement_id_list))
                logging.warning(f"There is a difference between proposed agreement list and agreement list. " +
                                f"Original list {', '.join([validator.hex for validator in proposed_agreement_list[:proposed_agreement_list_len]])} " +
                                f"Calculated list {', '.join(agreement_id_list)} ")
                add_agreement_result(False)
                continue

            possible_node_ids = [node["identifier"] for node in nodes[half_validator_len:]]
            for node_id in proposed_agreement_list[proposed_agreement_list_len / 2:]:
                if node_id not in possible_node_ids:
                    logging.warning(f"Node {node_id} not in possible nodes {', '.join(possible_node_ids)}")
                    add_agreement_result(False)
                    continue

            add_agreement_result(True)

    sleep(10)
