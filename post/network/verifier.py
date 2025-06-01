import logging
from time import sleep
from random import shuffle

import numpy as np

from post.network.blockchain import PoT
from post.network.transaction import TxToVerify


class TransactionVerifier:
    LOG_PREFIX = "TX_VERIFY: "
    pot: PoT
    stop: bool

    def __init__(self, pot: PoT):
        self.pot = pot
        self.stop = False


    def register_stop_handler(self):
        """
        Register stop handler for SIGINT
        :return:
        """
        import signal

        def stop_handler(signum, frame):
            logging.info(self.LOG_PREFIX + "Stop signal received")
            self.stop = True

        signal.signal(signal.SIGINT, stop_handler)

    # def start_thread(self):
    #     thread = Thread(target=self.process)
    #     thread.start()

    def process(self):
        logging.debug(self.LOG_PREFIX + "Start processing ")
        while True:
            if self.stop:
                logging.info(self.LOG_PREFIX + "Stop signal received. Exiting")
                break

            if not self.pot.nodes.is_validator(self.pot.self_node.get_node()):
                sleep(5)
                continue

            uuid_to_do = []
            for uuid, tx_to_verify in self.pot.tx_to_verified.all().items():
                if self.pot.self_node.identifier not in list(tx_to_verify.voting.keys()):
                    logging.debug(
                        self.LOG_PREFIX
                        + f"Transaction {uuid.hex} has no vote from self node {self.pot.self_node.identifier.hex}. Adding to verify. "
                        + f"Voting: " + ', '.join([f"{k.hex}-{v}" for k, v in tx_to_verify.voting.items()])
                    )
                    uuid_to_do.append(uuid)

            if not uuid_to_do:
                logging.debug(self.LOG_PREFIX + "Nothing to verify")
                sleep(1)
                continue

            logging.debug(
                self.LOG_PREFIX
                + f"Transactions {','.join([uid.hex for uid in uuid_to_do])} found to verify"
            )

            tx_uuid = None
            tx_to_verify = None
            shuffle(uuid_to_do)
            for uuid in uuid_to_do:
                tx_to_verify = self.pot.tx_to_verified.find(uuid)
                if tx_to_verify: #and tx_to_verify.voting.keys()
                    # For scaling reasons part of TxToVerified must be lock
                    tx_uuid = uuid
                    break

            if not tx_to_verify:
                logging.debug(self.LOG_PREFIX + f"Nothing to verify")
                continue

            logging.debug(
                self.LOG_PREFIX + f"Verifying transaction of id {tx_uuid.hex}"
            )
            try:
                result = self.verify_transaction(tx_to_verify)
                logging.info(
                    self.LOG_PREFIX
                    + f"Transaction {tx_uuid.hex} verified. Result: {result}"
                )
                self.pot.add_transaction_verification_result(
                    tx_uuid, self.pot.self_node.get_node(), result
                )
                self.pot.send_transaction_verification(tx_uuid, result)
            except Exception as e:
                logging.error(
                    self.LOG_PREFIX
                    + f"Error while verifying transaction of id {tx_uuid.hex}. Error: {e}"
                )

    def verify_transaction(self, tx_to_verify: TxToVerify) -> bool:
        special_prefix = self.LOG_PREFIX + " _special_ "
        tx = tx_to_verify.tx
        transaction_data_key = tx.DATA_KEY
        tx_type = tx.data.get(tx.TYPE_KEY)
        if tx_type == "0":
            logging.info(special_prefix + "Transaction type is 0. Skipping verification")
            return True
        last_txs = self.pot.blockchain.find_last_transactions_values_for_node(
            tx_to_verify.node, tx_type
        )
        str_data = ', '.join([str(tx['data'][transaction_data_key]) for tx in last_txs])
        logging.info(
            special_prefix
            + f"Found {len(last_txs)} Last transactions of type {tx_type} for node {tx_to_verify.node.identifier.hex}: {str_data}"
        )
        if len(last_txs) < 10:
            logging.info(
                special_prefix
                + f"Transaction type {tx_type} has less than 10 transactions. Skipping verification"
            )
            return True
        last_txs_data = [tx["data"][transaction_data_key] for tx in last_txs]
        mean = np.mean(last_txs_data)
        std = np.std(last_txs_data)
        logging.info(special_prefix + f"Mean: {mean}; Std: {std}")
        value = tx.data[transaction_data_key]
        res = bool(mean - 2.0 * std <= value <= mean + 2.0 * std)
        logging.info(
            special_prefix
            + f"Result of verifier: {str(res)}. Value: {value}; Mean: {mean}; Std: {std}; Data: {str_data}"
        )
        return res
