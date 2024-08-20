import logging
import random
from threading import Thread
from time import sleep, time
from math import ceil
from random import randint
from uuid import UUID

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

self_node = pot.self_node.get_node()


def add_agreement_result(result: bool):
    logging.warning(
        f"Validators list that is judged: {', '.join([vid.hex for vid in pot.nodes.validator_agreement.all()])}")
    logging.warning(f"Result of validation: {result} for node {self_node.identifier.hex}")


    pot.nodes.validator_agreement_result.add(self_node.identifier, result)
    vote_data = {
        "result": result
    }

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
logging.info(f"Node: {self_node.identifier}. Socket: {socket.gethostbyname(socket.gethostname())}")

try:
    while True:

        if not pot.nodes.is_validator(self_node):
            sleep(10)
            continue

        logging.info(f"Checking if validator has work to do: {self_node.identifier.hex}")
        agreement_info = pot.nodes.validator_agreement_info
        agreement_info.refresh()
        if agreement_info.is_started:
            if pot.nodes.validator_agreement_result.find(self_node.identifier) is None:
                logging.info("Validation is starting")
                proposed_agreement_list = pot.nodes.validator_agreement.all()

                if len(proposed_agreement_list) != len(set(proposed_agreement_list)):
                    logging.warning(f"There are duplicates in agreement list")
                    add_agreement_result(False)
                    continue
                logging.debug("There is no duplicates in agreement")

                nodes = pot.nodes.prepare_all_nodes_info()
                nodes = sorted(nodes, key=lambda node_info: node_info["trust"])
                validator_len = max(2, ceil(len(nodes) * 0.1))
                proposed_agreement_list_len = len(proposed_agreement_list)
                if validator_len != proposed_agreement_list_len:
                    logging.warning(f"Calculated length of nodes ({validator_len}) "
                                    f"is not equal agreement list ({proposed_agreement_list_len})")
                    add_agreement_result(False)
                    continue
                logging.debug("Length of agreement is the same")

                half_validator_len = int(validator_len / 2)
                agreement_list = nodes[0:half_validator_len]
                agreement_id_list = [UUID(hex=node["identifier"]) for node in agreement_list]

                # [validator.hex for validator in proposed_agreement_list[:proposed_agreement_list_len]]
                if proposed_agreement_list[:half_validator_len] != agreement_id_list:
                    diff = set(proposed_agreement_list[:half_validator_len]).difference(set(agreement_id_list))
                    logging.warning(f"There is a difference between proposed agreement list and agreement list. " +
                                    f"Original list {', '.join([validator.hex for validator in proposed_agreement_list[:half_validator_len]])} " +
                                    f"Calculated list {', '.join([node_id.hex for node_id in agreement_id_list])} " +
                                    f"Diff: {', '.join([node_id.hex for node_id in list(diff)])}")
                    add_agreement_result(False)
                    continue
                logging.debug("First part of agreement is the same")

                possible_node_ids = [UUID(hex=node["identifier"]) for node in nodes[half_validator_len:]]
                logging.debug(f"Possible nodes id {', '.join([node_id.hex for node_id in possible_node_ids])}")
                not_valid = True
                second_part_of_agreement_list = proposed_agreement_list[half_validator_len:]
                logging.debug(f"Second part of agreement {', '.join([node_id.hex for node_id in second_part_of_agreement_list])}")
                for node_id in second_part_of_agreement_list:
                    logging.debug(f"Checking node {node_id.hex} in {', '.join([node_id_agreement.hex for node_id_agreement in second_part_of_agreement_list])}")
                    if node_id not in possible_node_ids:
                        logging.debug(f"Node {node_id} not in possible nodes {', '.join([node_id.hex for node_id in possible_node_ids])}")
                        not_valid = False
                        break

                logging.debug(f"Second part of agreement result is {not_valid}")
                add_agreement_result(not_valid)

        sleep(10)
except Exception as e:
    logging.error(f"Error: {e}")
