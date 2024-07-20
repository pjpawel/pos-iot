import logging
from uuid import UUID

import requests

from pot.network.exception import PublicKeyNotFoundException


class Request:

    @staticmethod
    def get_public_key(host: str, port: int) -> bytes:
        response = requests.get(f"http://{host}:{port}/public-key")
        if response.status_code != 200:
            raise PublicKeyNotFoundException(f"Cannot get public key from node: {host}:{port}")
        return response.content

    @staticmethod
    def get_info(host: str, port: int) -> dict:
        response = requests.get(f"http://{host}:{port}/info")
        if response.status_code != 200:
            raise Exception(f"Cannot get info from host: {host}:{port}")
        return response.json()

    @staticmethod
    def send_transaction_populate(host: str, port: int, identifier: str, data: bytes) -> None:
        response = requests.post(f"http://{host}:{port}/transaction/{identifier}/populate", data)
        if response.status_code != 200:
            raise Exception(f"Cannot send populate verification result to host: {host}:{port}")

    @staticmethod
    def send_populate_verification_result(host: str, port: int, identifier: str, data: dict) -> None:
        response = requests.post(f"http://{host}:{port}/transaction/{identifier}/verifyResult", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot send populate verification result to host: {host}:{port} response: {response.text.encode('utf-8')}")

    @staticmethod
    def send_transaction_get_info(host: str, port: int, identifier: str) -> bytes:
        response = requests.get(f"http://{host}:{port}/transaction/{identifier}")
        if response.status_code != 200:
            raise Exception(f"Cannot get transaction from host: {host}:{port}")
        return response.content

    @staticmethod
    def send_blockchain_new_block(host: str, port: int, data: bytes) -> None:
        logging.info(f"Sending new block to host: {host}:{port}")
        response = requests.post(f"http://{host}:{port}/blockchain/block/new", data)
        if response.status_code != 200:
            msg = f"Cannot send new block to host: {host}:{port}"
            logging.warning(msg)
            raise Exception(msg)
        logging.info(f"New block send to node in {host}:{port}")

    @staticmethod
    def send_node_trust_change(host: str, port: int, node_id: UUID, data: dict) -> None:
        response = requests.patch(f"http://{host}:{port}/node/{node_id.hex}/trust", json=data)
        if response.status_code >= 300:
            raise Exception(f"Cannot send change node trust for node {node_id.hex}, data: {response.request.body} sending to {host}:{port}, response: {response.text}")
