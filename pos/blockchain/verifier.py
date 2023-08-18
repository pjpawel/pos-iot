import logging
from threading import Thread
from time import sleep

from pos.blockchain.blockchain import PoS
from pos.blockchain.transaction import TxToVerify


class TransactionVerifier:
    pos: PoS

    def __init__(self, pos: PoS):
        self.pos = pos

    def _start(self):
        thread = Thread(target=self.process)
        thread.start()

    def process(self):
        while True:
            if self.pos.tx_to_verified:
                uuid = list(self.pos.tx_to_verified.keys())[0]
                tx_to_verify = self.pos.tx_to_verified.pop(uuid)
                try:
                    result = self.verify_transaction(tx_to_verify)
                    self.pos.send_transaction_verification(uuid, tx_to_verify, result)
                except Exception as e:
                    logging.error(e)
            else:
                sleep(1)

    def verify_transaction(self, tx: TxToVerify) -> bool:
        """
        Verify transaction based on previous records
        :param tx:
        :return:
        """
        # TODO:
        return True
