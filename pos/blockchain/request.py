import requests

from pos.blockchain.exception import PublicKeyNotFoundException


def get_public_key(host: str, port: int) -> bytes:
    response = requests.get(f"http://{host}:{port}/public-key")
    if response.status_code != 200:
        raise PublicKeyNotFoundException(f"Cannot get public key from node: {host}:{port}")
    return response.content


def get_info(host: str, port: int) -> dict:
    response = requests.get(f"http::/{host}:{port}/info")
    if response.status_code != 200:
        raise Exception(f"Cannot get info from host: {host}:{port}")
    return response.json()
