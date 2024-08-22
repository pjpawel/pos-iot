import logging
from threading import Thread
from time import sleep
from random import shuffle

from pot.network.blockchain import PoT
from pot.network.transaction import TxToVerify


class TransactionVerifier:
    LOG_PREFIX = 'TX_VERIFY: '
    pot: PoT

    def __init__(self, pot: PoT):
        self.pot = pot

    def start_thread(self):
        thread = Thread(target=self.process)
        thread.start()

    def process(self):
        logging.debug(self.LOG_PREFIX + "Start processing ")
        while True:

            if not self.pot.nodes.is_validator(self.pot.self_node.get_node()):
                sleep(5)
                continue

            uuid_to_do = []
            for uuid, tx_to_verify in self.pot.tx_to_verified.all().items():
                if self.pot.self_node.identifier not in list(tx_to_verify.voting.keys()):
                    uuid_to_do.append(uuid)

            if uuid_to_do:
                logging.debug(
                    self.LOG_PREFIX + f"Transactions {','.join([uid.hex for uid in uuid_to_do])} found to verify")

                tx_uuid = None
                tx_to_verify = None
                shuffle(uuid_to_do)
                for uuid in uuid_to_do:
                    tx_to_verify = self.pot.tx_to_verified.find(uuid)
                    if tx_to_verify:
                        # For scaling reasons part of TxToVerified must be lock
                        tx_uuid = uuid
                        break

                if not tx_to_verify:
                    logging.debug(self.LOG_PREFIX + f"Nothing to verify")
                    continue

                logging.debug(self.LOG_PREFIX + f"Verifying transaction of id {tx_uuid.hex}")
                try:
                    result = self.verify_transaction(tx_to_verify)
                    logging.info(self.LOG_PREFIX + f"Transaction {tx_uuid.hex} verified. Result: {result}")
                    self.pot.add_transaction_verification_result(tx_uuid, self.pot.self_node.get_node(), result)
                    self.pot.send_transaction_verification(tx_uuid, result)
                except Exception as e:
                    logging.error(self.LOG_PREFIX + f"Error while verifying transaction of id {tx_uuid.hex}. Error: {e}")
            else:
                logging.debug(self.LOG_PREFIX + "Nothing to verify")
                sleep(1)

    def verify_transaction(self, tx_to_verify: TxToVerify) -> bool:
        """
        Verify transaction based on previous records
        :param tx_to_verify:
        :return:
        """
        tx = tx_to_verify.tx
        tx_type = tx.data.get(tx.TYPE_KEY)
        if tx_type == "0":
            return True
        last_txs = self.pot.blockchain.find_last_transactions_values_for_node(tx_to_verify.node, tx_type)
