from time import sleep
import requests

from utils import get_random_from_list


def instant_sender(nodes):
    """

    :param nodes: Node
    :return:
    """
    while True:
        sleep(5)
        node = get_random_from_list(nodes)
        requests.post(f"http://{node.host}:{node.port}/transaction", {
            # TODO: generate random data with signature of sender
        })


def mad_sender(nodes):
    while True:
        sleep(5)
        node = get_random_from_list(nodes)
        requests.post(f"http://{node.host}:{node.port}/transaction", {
            # TODO: generate random data with signature of sender
        })


def simple_sender(nodes):
    while True:
        sleep(5)
        node = get_random_from_list(nodes)
        requests.post(f"http://{node.host}:{node.port}/transaction", {
            # TODO: send the same data with signature of sender
        })
