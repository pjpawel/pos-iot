import logging
from threading import Thread
from time import sleep
from random import shuffle

from pos.network.blockchain import PoS
from pos.network.transaction import TxToVerify


class TransactionVerifier:
    LOG_PREFIX = 'TX_VERIFY: '
    pos: PoS

    def __init__(self, pos: PoS):
        self.pos = pos

    def start_thread(self):
        thread = Thread(target=self.process)
        thread.start()

    def process(self):
        logging.info(self.LOG_PREFIX + "Start processing ")
        while True:
            self.pos.tx_to_verified.refresh()
            uuid_to_do = []
            for uuid, tx_to_verify in self.pos.tx_to_verified.all().items():
                if self.pos.self_node.identifier not in list(tx_to_verify.voting.keys()):
                    uuid_to_do.append(uuid)

            if uuid_to_do:
                logging.info(
                    self.LOG_PREFIX + f"Transactions {','.join([uid.hex for uid in uuid_to_do])} found to verify")

                tx_uuid = None
                tx_to_verify = None
                shuffle(uuid_to_do)
                for uuid in uuid_to_do:
                    tx_to_verify = self.pos.tx_to_verified.find(uuid)
                    if tx_to_verify:
                        # For scaling reasons part of TxToVerified must be lock
                        tx_uuid = uuid
                        break

                if not tx_to_verify:
                    logging.debug(self.LOG_PREFIX + f"Nothing to verify")
                    continue

                logging.info(self.LOG_PREFIX + f"Verifying transaction of id {tx_uuid.hex}")
                try:
                    result = self.verify_transaction(tx_to_verify)
                    logging.info(self.LOG_PREFIX + f"Transaction {tx_uuid.hex} verified. Result: {result}")
                    self.pos.add_transaction_verification_result(tx_uuid, self.pos.self_node, result)
                    self.pos.send_transaction_verification(tx_uuid, result)
                except Exception as e:
                    logging.error(self.LOG_PREFIX + f"Error while verifying transaction of id {tx_uuid.hex}. Error: {e}")
            else:
                logging.debug(self.LOG_PREFIX + "Nothing to verify")
                sleep(1)

    def verify_transaction(self, tx: TxToVerify) -> bool:
        """
        Verify transaction based on previous records
        :param tx:
        :return:
        """
        # TODO:
        return True
