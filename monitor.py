import csv
import datetime
import os
import random
from copy import copy
from uuid import UUID
from pprint import pprint
import itertools

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from dotenv import load_dotenv
from requests.utils import rewind_body

from pot.network.dumper import Dumper
from pot.network.manager import NodeTrust
from pot.monitor.imports import (
    get_self_node_info,
    get_info_from_blockchain,
    get_info_from_nodes, get_info_from_validators, get_info_from_transactions_to_verify,
    get_info_from_transactions_verified, get_transactions_times, get_transactions_times_values,
)

storage_path = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "storage")
)
result_path = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "monitor", "result")
)

#firsts_records = 10000
firsts_records = None   # None|10000

load_dotenv()

##############################################
cols_dict = {
    "time": "Time",
    "number_of_nodes": "Number of nodes",
    "number_of_validators": "Number of validators",
    # 'node_trust': 'Node trust',
    "number_of_blocks": "Number of blocks",
    "number_of_transaction_to_verify": "Number of transactions to verify",
    "number_of_verified_transactions": "Number of verified transactions",
    "validators": "Validators",
}

translation = {
    "Time [s]": "Czas [s]",
    "number of nodes": "Liczba węzłów",
    "number of validators": "Liczba walidatorów",
    "number of blocks": "Liczba bloków",
    "number of transaction to verify": "Liczba transakcji do weryfikacji",
    "number of verified transactions": "Liczba zweryfikowanych transakcji",
    "validators": "Walidatorzy",
}

markers = ["1","2","3","4","8","s","p","P","*","h","H","+","x","X","D","d","|","_",]
line_styles = ["-", "--", ":", "-."]
styles = itertools.cycle([marker + line for marker in markers for line in line_styles])

cols = list(cols_dict.keys())

df_trust = pd.DataFrame(columns=["time", "sourceNode", "node", "trust"])
df_trust.set_index(["time", "sourceNode", "node"], inplace=True)
# df_trust.sort_index()

first_time = None
dfs = {}
transaction_times = []
nodes_mapping = {}
last_trust = {}

for node in os.listdir(storage_path):
    # list all nodes in dir
    if node == ".gitignore":
        continue
    print(f"Processing node {node}")

    trust_data = []

    df = pd.DataFrame(columns=cols)
    df.set_index("time", inplace=True)

    dirs = [int(time_dir) for time_dir in os.listdir(os.path.join(storage_path, node, "dump"))]
    dirs.sort()
    print(f"Found {len(dirs)} dirs in node {node}")


    storage_dir = os.path.join(storage_path, node, "storage")
    # Get all transactions time
    transaction_times.extend(get_transactions_times_values(storage_dir))
    # Get last trust
    self_node_id = get_self_node_info(storage_dir)
    all_node_trust = get_info_from_nodes(storage_dir)["trust"]
    last_trust[self_node_id] = all_node_trust


    record_i = 0
    for time in dirs:
        time_int = int(time)
        time = float(time) / Dumper.SECOND_PART
        # list all time in dir
        if not first_time:
            first_time = time

        if firsts_records is not None:
            if firsts_records < record_i:
                break

        storage_dir = os.path.join(storage_path, node, "dump", str(time_int))
        # print(f"Processing dir {storage_dir}")

        if node not in nodes_mapping.keys():
            self_node_id = get_self_node_info(storage_dir)
            nodes_mapping[node] = self_node_id.hex
            print(self_node_id.hex)

        try:
            # self_node_id = get_self_node_info(storage_dir)
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
            nodes_info["len"],
            validators_info["len"],
            # nodes_info["trust"],
            blocks_info["len"],
            txs_to_ver_info["len"],
            txs_ver_info["len"],
            validators_info["validators"],
        ]
        for node_id, trust in nodes_info["trust"].items():
            trust_data.append(
                {
                    "time": actual_time,
                    "sourceNode": node,
                    "node": node_id.hex,
                    "trust": trust,
                }
            )
            # df_trust.loc[(actual_time, node, node_id.hex), :] = trust
        record_i += 1

    # check if all df has step by step info
    # df.to_excel(os.path.join(result_path, f"result-{node}.xlsx"))
    dfs[node] = df

    df_trust_node = pd.DataFrame(
        trust_data, columns=["time", "sourceNode", "node", "trust"]
    )
    df_trust_node.set_index(["time", "sourceNode", "node"], inplace=True)
    # df_trust_node.to_excel(os.path.join(result_path, f"result-trust-{node}.xlsx"))
    df_trust = pd.concat([df_trust, df_trust_node])

#df_trust.to_excel(os.path.join(result_path, "result-trust.xlsx"))

print("")
import datetime

first_time = int(first_time / Dumper.SECOND_PART)
first_time_date = datetime.datetime.fromtimestamp(first_time, datetime.timezone.utc)
print(f"First time: {first_time} - {first_time_date.isoformat()} UTC")
print("")

random_df = dfs.get(list(dfs.keys())[random.randint(0, len(dfs.keys()) - 1)])
for validators_str in random_df["validators"].unique():
    df_validators = random_df[random_df["validators"] == validators_str]
    print(
        f"Validators: {validators_str}. Index min: {df_validators.first_valid_index()}. Index max: {df_validators.last_valid_index()}"
    )
print("")

"""
Calculate transaction times
"""
if not transaction_times:
    print("No transaction times")
else:
    tx_min = min(transaction_times)
    tx_max = max(transaction_times)
    tx_mean = np.mean(transaction_times)
    tx_std = np.std(transaction_times)
    tx_q1 = np.percentile(transaction_times, 25)
    tx_q3 = np.percentile(transaction_times, 75)

    print("Transaction times")
    print(f"Median: {np.median(transaction_times)}")
    print(f"Min: {tx_min}")
    print(f"Max: {tx_max}")
    print(f"Mean: {tx_mean}")
    print(f"Std: {tx_std}")
    print(f"Q1: {tx_q1}")
    print(f"Q3: {tx_q3}")
    print("")

    with open(os.path.join(result_path, "result_tx.csv"), "w") as f:
        csv.writer(f).writerows([transaction_times])


"""
Save last trust
"""
trusts = []
node_to_cover = []
for node_id, trust in last_trust.items():
    value = trust.get(node_id, None)
    if value is None:
        node_to_cover.append(node_id)
    else:
        trusts.append(value)

for node_id in node_to_cover:
    list_values = [value.get(node_id, np.nan) for value in list(last_trust.values())]
    new_values = [value for value in list_values if value is not np.nan]
    if not new_values:
        print(f"Node {node_id} not found in last trust")
        new_values = [5000]
    value = np.mean(new_values)
    trusts.append(value)


print("Info about last trust")
#trust_values = list(last_trust.values())
trust_values = trusts
if not trust_values:
    print("No trust values")
else:
    trust_mean = np.mean(trust_values)
    trust_std = np.std(trust_values)
    trust_q1 = np.percentile(trust_values, 25)
    trust_q3 = np.percentile(trust_values, 75)
    trust_median = np.median(trust_values)
    trust_max = max(trust_values)
    trust_min = min(trust_values)
    print(f"Median: {trust_median}")
    print(f"Mean: {trust_mean}")
    print(f"Std: {trust_std}")
    print(f"Q1: {trust_q1}")
    print(f"Q3: {trust_q3}")
    print(f"Max: {trust_max}")
    print(f"Min: {trust_min}")
    print("")

    with open(os.path.join(result_path, "result_trust_values.csv"), "w") as f:
        writer = csv.writer(f)
        writer.writerow(trusts)
        # for node, trust in last_trust.items():
        #     writer.writerow([node, trust])

    with open(os.path.join(result_path, "result_trust.csv"), "w") as f:
        csv.writer(f).writerow([trust_median, trust_mean, trust_std, trust_q1, trust_q3, trust_max, trust_min])


"""
Plotting
"""
for node, df in dfs.items():
    df.drop(columns=["validators"], inplace=True)

# check if all df has step by step info
for col in cols[1 : len(cols) - 2]:
    max_value = 0
    data = {}
    for node, df in dfs.items():
        data[node] = df[col]
        if max_value < df[col].max():
            max_value = df[col].max()

    # Standard plot all of data
    df_show = pd.DataFrame(data)
    print(f"\nProcessing column {col}")

    col_name = col.replace("_", " ")
    style_list = [next(styles) for _ in df_show.columns]
    df_show.plot(
        style=style_list,
        legend=True,
        #title=f"Plot {col} against time",
        xlabel="Time [s]",
        ylabel=col_name.capitalize(),
        ylim=(max(0, int(-max_value * 0.1)), max_value + max_value * 0.1),
        grid=True,
    )
    #plt.savefig(os.path.join(result_path, f"plot-{col}.pdf"))
    plt.savefig(os.path.join(result_path, f"plot-{col}.png"))
    plt.close()

    df_show.plot(
        style=style_list,
        legend=True,
        # title=f"Plot {col} against time",
        xlabel="Czas [s]",
        ylabel=translation[col_name],
        ylim=(max(0, int(-max_value * 0.1)), max_value + max_value * 0.1),
        grid=True,
    )
    #plt.savefig(os.path.join(result_path, f"plot-pl-{col}.pdf"))
    plt.savefig(os.path.join(result_path, f"plot-pl-{col}.png"))
    plt.close()

    # Plot of change

    random_data = random.choice(list(data.values()))
    print("Unique values")
    pprint(random_data.unique())
    if len(random_data.unique()) <= 1:
        random_change = random_data.unique()[0]
    else:
        while True:
            random_change = random.choice(random_data.unique())
            if random_change is not np.nan and random_change != 0:
                break
    print("Change: " + str(random_change))
    first_idx = random_data[random_data == random_change].first_valid_index()
    print("First index on int: " + str(int(first_idx)))
    # first_idx = int(float(first_idx) * Dumper.SECOND_PART)
    # print("First index on float: " + str(first_idx))

    df_show = df_show.loc[first_idx - 2.0: first_idx + 2.0]
    style_list = [next(styles) for _ in df_show.columns]
    col_name = col.replace("_", " ")
    df_show.plot(
        style=style_list,
        legend=True,
        #title=f"Plot {col_name} against time - change near {round(first_idx, 0)} second",
        xlabel="Time [s]",
        ylabel=col_name.capitalize(),
        # ylim=(max(0, int(-max_value * 0.1)), max_value + max_value * 0.1),
        grid=True,
    )
    #plt.figure().gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    #plt.savefig(os.path.join(result_path, f"plot-{col}-part.pdf"))
    plt.savefig(os.path.join(result_path, f"plot-{col}-part.png"))
    plt.close()

    df_show.plot(
        style=style_list,
        legend=True,
        xlabel="Czas [s]",
        ylabel=translation[col_name],
        # ylim=(max(0, int(-max_value * 0.1)), max_value + max_value * 0.1),
        grid=True,
    )
    #plt.savefig(os.path.join(result_path, f"plot-pl-{col}.pdf"))
    plt.savefig(os.path.join(result_path, f"plot-pl-{col}.png"))
    plt.close()

print("")
nodes_ids = df_trust.reset_index()["node"].unique()

print("Nodes map")
pprint(nodes_mapping)
print("Nodes")
pprint(nodes_ids)

styles = itertools.cycle([marker + line for marker in markers for line in line_styles])

for node_id in nodes_ids:
    if node_id not in list(nodes_mapping.values()):
        print(f"{node_id} not found in nodes_mapping")
        continue
    node_name = list(nodes_mapping.keys())[list(nodes_mapping.values()).index(node_id)]

    print(f"Processing trust for node {node_id} => {node_name}")
    # Plot trust for node - all
    pivot = (
        df_trust.xs(node_id, level=2)
        .reset_index()
        .pivot(index="time", columns="sourceNode", values="trust")
    )
    style_list = [next(styles) for _ in pivot.columns]
    pivot.plot(
        style=style_list,
        legend=True,
        #title=f"Change of trust for node {node_name} in time",
        xlabel="Time [s]",
        ylabel="Trust",
        grid=True,
    )
    # (df_trust.xs(node_id, level=2)
    #     .reset_index()
    #     .pivot(index='time', columns='sourceNode', values='trust')
    #     .plot(kind='line', figsize=(10, 6), style=style_list))
    #plt.title(f"Change of trust for node {node_name} in time ")
    plt.xlabel("Time [s]")
    plt.ylabel("Level of Trust")
    plt.legend(title="Source node")
    plt.grid(True)
    #plt.savefig(os.path.join(result_path, f"plot-trust-{node_name}.pdf"))
    plt.savefig(os.path.join(result_path, f"plot-trust-{node_name}.png"))
    plt.close()

    pivot.plot(
        style=style_list,
        legend=True,
        # title=f"Change of trust for node {node_name} in time",
        xlabel="Czas [s]",
        ylabel="Poziom zaufania",
        grid=True,
    )
    #plt.savefig(os.path.join(result_path, f"plot-pl-trust-{node_name}.pdf"))
    plt.savefig(os.path.join(result_path, f"plot-pl-trust-{node_name}.png"))
    plt.close()

    # Plot trust for node - part
    while True:
        random_column = random.choice(pivot.columns)
        random_trust = random.choice(pivot[random_column].unique())
        if random_trust is not np.nan or random_trust == NodeTrust.BASIC_TRUST:
            break
    print("Trust: " + str(int(random_trust)))
    first_idx = pivot[pivot[random_column] == random_trust].first_valid_index()
    print("First index: " + str(int(first_idx)))

    pivot = pivot.loc[first_idx - 2: first_idx + 2]
    style_list = [next(styles) for _ in pivot.columns]
    # pivot.plot(
    #     style=style_list,
    #     legend=True,
    #     #title=f"Change of trust for node {node_name} in time - change near {round(first_idx, 2)} second",
    #     xlabel="Time [s]",
    #     ylabel="Trust",
    #     grid=True,
    # )
    ## plt.title(f"Change of trust for node {node_name} in time - change near {first_idx} second")


    # plt.xlabel('Time [s]')
    # plt.ylabel('Trust')
    # plt.legend(title="Source node")
    # plt.grid(True)
    # plt.savefig(os.path.join(result_path, f"plot-trust-{node_name}-part.pdf"))
    # plt.savefig(os.path.join(result_path, f"plot-trust-{node_name}-part.png"))
    #
    # plt.xlabel("Czas [s]")
    # plt.ylabel("Poziom zaufania")
    #
    # plt.savefig(os.path.join(result_path, f"plot-pl-trust-{node_name}-part.pdf"))
    # plt.savefig(os.path.join(result_path, f"plot-pl-trust-{node_name}-part.png"))
    plt.close()
