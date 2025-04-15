import os
from uuid import UUID

from pot.network.manager import NodeTrust
from pot.network.node import SelfNodeInfo
from pot.network.storage import TransactionTime, NodeStorage, NodeTrustStorage, ValidatorStorage, TransactionStorage, \
    TransactionVerifiedStorage, BlocksStorage


def get_transactions_times(storage_path: str) -> dict[UUID, tuple[bool, float]]:
    storage = TransactionTime(storage_path)
    return storage.load()

def get_transactions_times_values(storage_path: str) -> list[float]:
    transaction_times = get_transactions_times(storage_path)
    return [v[1] for v in transaction_times.values()]

def get_self_node_info(path: str) -> UUID:
    old_value = os.getenv("STORAGE_DIR")
    os.environ["STORAGE_DIR"] = path
    self_node = SelfNodeInfo(True)
    os.environ["STORAGE_DIR"] = old_value
    return self_node.identifier


def get_info_from_blockchain(path: str) -> dict:
    storage = BlocksStorage(path)
    blocks = storage.load()
    return {
        "len": len(blocks),
        "transaction_len": sum([len(block.transactions) for block in blocks]),
    }


def get_info_from_nodes(path: str) -> dict:
    storage = NodeStorage(path)
    nodes = storage.load()
    trust = NodeTrust.__new__(NodeTrust)
    trust._storage = NodeTrustStorage(path)
    # trust._storage.load()
    # print(f"Trust from {path}: {trust._storage.load()}")
    # old_value = os.getenv('STORAGE_DIR')
    # os.putenv('STORAGE_DIR', path)
    # self_node = SelfNodeInfo()
    # os.putenv('STORAGE_DIR', old_value)
    return {
        "len": len(nodes),
        # "trust": trust.get_node_trust(self_node.get_node())
        "trust": trust._storage.load(),
    }


def get_info_from_validators(path: str) -> dict:
    storage = ValidatorStorage(path)
    validators = storage.load()
    return {"len": len(validators), "validators": ",".join([v.hex for v in validators])}


def get_info_from_transactions_to_verify(path: str) -> dict:
    storage = TransactionStorage(path)
    try:
        txs = storage.load()
    except Exception as e:
        print(f"Error while processing transactions from path {storage.path}: {e}")
        txs = []
    return {"len": len(txs)}


def get_info_from_transactions_verified(path: str) -> dict:
    storage = TransactionVerifiedStorage(path)
    txs = storage.load()
    return {"len": len(txs)}
