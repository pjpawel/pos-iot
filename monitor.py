import datetime
import os
from uuid import UUID
from pprint import pprint

import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

from pot.network.node import SelfNodeInfo
from pot.network.storage import BlocksStorage, NodeStorage, TransactionStorage, NodeTrustStorage, ValidatorStorage, \
    TransactionVerifiedStorage
from pot.network.manager import NodeTrust

storage_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'storage'))
result_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'monitor', 'result'))

firsts_records = 1000

load_dotenv()


def get_self_node_info(path: str) -> UUID:
    old_value = os.getenv('STORAGE_DIR')
    os.environ["STORAGE_DIR"] = path
    self_node = SelfNodeInfo(True)
    os.environ["STORAGE_DIR"] = old_value
    return self_node.identifier


def get_info_from_blockchain(path: str) -> dict:
    storage = BlocksStorage(path)
    blocks = storage.load()
    return {
        "len": len(blocks),
        "transaction_len": sum([len(block.transactions) for block in blocks])
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
        #"trust": trust.get_node_trust(self_node.get_node())
        "trust": trust._storage.load()
    }


def get_info_from_validators(path: str) -> dict:
    storage = ValidatorStorage(path)
    validators = storage.load()
    return {
        "len": len(validators)
    }


def get_info_from_transactions_to_verify(path: str) -> dict:
    storage = TransactionStorage(path)
    try:
        txs = storage.load()
    except Exception as e:
        print(f"Error while processing path {path}: {e}")
        txs = []
    return {
        "len": len(txs)
    }


def get_info_from_transactions_verified(path: str) -> dict:
    storage = TransactionVerifiedStorage(path)
    txs = storage.load()
    return {
        "len": len(txs)
    }


cols_dict = {
    'time': 'Time',
    'number_of_nodes': 'Number of nodes',
    'number_of_validators': 'Number of validators',
    # 'node_trust': 'Node trust',
    'number_of_blocks': 'Number of blocks',
    'number_of_transaction_to_verify': 'Number of transactions to verify',
    'number_of_verified_transactions': 'Number of verified transactions',
}

cols = list(cols_dict.keys())

df_trust = pd.DataFrame(columns=["time", "sourceNode", "node", "trust"])
df_trust.set_index(["time", "sourceNode", "node"], inplace=True)
# df_trust.sort_index()

first_time = None
dfs = {}

nodes_mapping = {}

for node in os.listdir(storage_path):
    # list all nodes in dir

    if node == '.gitignore':
        continue

    print(f"Processing node {node}")

    trust_data = []

    df = pd.DataFrame(columns=cols)
    df.set_index('time', inplace=True)

    dirs = [int(time_dir) for time_dir in os.listdir(os.path.join(storage_path, node, 'dump'))]
    dirs.sort()
    print(f"Found {len(dirs)} dirs in node {node}")

    record_i = 0
    for time in dirs:
        # list all time in dir
        if not first_time:
            first_time = time

        if firsts_records is not None and firsts_records < record_i:
            break

        storage_dir = os.path.join(storage_path, node, 'dump', str(time))
        # print(f"Processing dir {storage_dir}")

        if node not in nodes_mapping.keys():
            self_node_id = get_self_node_info(storage_dir)
            nodes_mapping[node] = self_node_id.hex
            print(self_node_id.hex)

        try:
            #self_node_id = get_self_node_info(storage_dir)
            blocks_info = get_info_from_blockchain(storage_dir)
            nodes_info = get_info_from_nodes(storage_dir)
            validators_info = get_info_from_validators(storage_dir)
            txs_to_ver_info = get_info_from_transactions_to_verify(storage_dir)
            txs_ver_info = get_info_from_transactions_verified(storage_dir)
        except Exception as e:
            print(f"Exception {e} while loading from node: {node} from time {time}")
            raise e

        actual_time = time - first_time
        df.loc[actual_time] = [
            nodes_info['len'],
            validators_info['len'],
            # nodes_info["trust"],
            blocks_info['len'],
            txs_to_ver_info['len'],
            txs_ver_info['len']
        ]
        for node_id, trust in nodes_info["trust"].items():
            trust_data.append({
                "time": actual_time,
                "sourceNode": node,
                "node": node_id.hex,
                "trust": trust
            })
            # df_trust.loc[(actual_time, node, node_id.hex), :] = trust
        record_i += 1

    # check if all df has step by step info
    #df.to_excel(os.path.join(result_path, f"result-{node}.xlsx"))
    dfs[node] = df

    df_trust_node = pd.DataFrame(trust_data, columns=["time", "sourceNode", "node", "trust"])
    df_trust_node.set_index(["time", "sourceNode", "node"], inplace=True)
    #df_trust_node.to_excel(os.path.join(result_path, f"result-trust-{node}.xlsx"))

    df_trust = pd.concat([df_trust, df_trust_node])

df_trust.to_excel(os.path.join(result_path, "result-trust.xlsx"))

print("")
import datetime
first_time_date = datetime.datetime.fromtimestamp(first_time, datetime.timezone.utc)
print(f"First time: {first_time} - {first_time_date.isoformat()} UTC")
print("")

# check if all df has step by step info
# TODO: uncomment
for col in cols[1:]:
    max_value = 0
    data = {}
    for node, df in dfs.items():
        data[node] = df[col]
        if max_value < df[col].max():
            max_value = df[col].max()
        # if not index:
        #     index = df['time']

    df_show = pd.DataFrame(data)
    print(f"Processing column {col}")
    #print(df_show.info())
    #print(df_show.head())
    # df_show.plot(
    #     legend=True,
    #     title=f"Plot {col} against time",
    #     xlabel="Time [s]",
    #     ylabel=col,
    #     #        subplots=True,
    #     ylim=(-max_value*0.1, max_value + max_value*0.1),
    #     grid=True
    # )
    df_show.plot(
        # style=['+-', '.--'],
        legend=True,
        title=f"Plot {col} against time",
        xlabel="Time [s]",
        # subplots=True,
        ylim=(max(0, int(-max_value * 0.1)), max_value + max_value * 0.1),
        grid=True
    )
    plt.savefig(os.path.join(result_path, f"plot-{col}.png"))

print("")
nodes_ids = df_trust.reset_index()["node"].unique()

print("Nodes map")
pprint(nodes_mapping)
print("Nodes")
pprint(nodes_ids)

for node_id in nodes_ids:
    if node_id not in list(nodes_mapping.values()):
        print(f"{node_id} not found in nodes_mapping")
        continue
    node_name = list(nodes_mapping.keys())[list(nodes_mapping.values()).index(node_id)]

    print(f"Processing trust for node {node_id} => {node_name}")
    (df_trust.xs(node_id, level=2)
        .reset_index()
        .pivot(index='time', columns='sourceNode', values='trust')
        .plot(kind='line', figsize=(10, 6)))
    plt.title(f"Change of trust for node {node_name} in time ")
    plt.xlabel('Time [s]')
    plt.ylabel('Trust')
    plt.legend(title='Source node')
    plt.grid(True)
    plt.savefig(os.path.join(result_path, f"plot-trust-{node_name}.png"))
