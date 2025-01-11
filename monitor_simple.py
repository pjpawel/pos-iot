import os

import pandas
from matplotlib.pyplot import savefig
import matplotlib.pyplot as plt

from pot.network.storage import BlocksStorage, NodeStorage, TransactionStorage

storage_path = os.path.join(os.path.dirname(__file__), "monitor", "storage")
result_path = os.path.join(os.path.dirname(__file__), "monitor", "result")


def get_info_from_blockchain(path: str) -> dict:
    storage = BlocksStorage(path)
    blocks = storage.load()
    return {"len": len(blocks)}


def get_info_from_nodes(path: str) -> dict:
    storage = NodeStorage(path)
    nodes = storage.load()
    return {"len": len(nodes), "trust": {f"{node.identifier.hex}": 0 for node in nodes}}


def get_info_from_transactions_to_verify(path: str) -> dict:
    storage = TransactionStorage(path)
    txs = storage.load()
    return {"len": len(txs)}


def get_info_from_transactions_verified(path: str) -> dict:
    storage = TransactionStorage(path)
    txs = storage.load()
    return {"len": len(txs)}


cols = [
    "time",
    "node",
    "number_of_nodes",
    "node_trust",
    "number_of_blocks",
    "number_of_transaction_to_verify",
    "number_of_verified_transactions",
]

df = pandas.DataFrame(columns=cols)
df.set_index(["time", "node"])
first_time = None

for node in os.listdir(storage_path):
    # list all nodes in dir

    if node == ".gitignore":
        continue

    dirs = [int(dir) for dir in os.listdir(os.path.join(storage_path, node))]
    dirs.sort()

    for time in dirs:
        # list all time in dir
        if not first_time:
            first_time = time

        storage_dir = os.path.join(storage_path, node, str(time))
        print(f"Processing dir {storage_dir}")

        try:
            blocks_info = get_info_from_blockchain(storage_dir)
            nodes_info = get_info_from_nodes(storage_dir)
            txs_to_ver_info = get_info_from_transactions_to_verify(storage_dir)
            txs_ver_info = get_info_from_transactions_verified(storage_dir)
        except Exception as e:
            print(f"Exception {e} while loading from node: {node} from time {time}")
            raise e

        df.loc[len(df.index)] = [
            time - first_time,
            node,
            nodes_info["len"],
            0,
            blocks_info["len"],
            txs_to_ver_info["len"],
            txs_ver_info["len"],
        ]

print(df.groupby("node").groups)
# exit()

for col in cols[2:]:
    df.groupby("node").plot(x="time", y=col, legend=True)
    savefig(os.path.join(result_path, f"plot-{col}.png"))

df.to_excel(os.path.join(result_path, "result.xlsx"))
