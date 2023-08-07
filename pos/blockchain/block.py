import json
from .transaction import Transaction


class Block:
    timestamp: int
    prev_hash: str
    data: list[Transaction]
    validator: str
    signature: str

    def to_json(self):
        return json.dumps(
            {
                'timestamp': self.timestamp,
                'prev_hash': self.signature,
                'data': [transaction.to_json() for transaction in self.data],
                'validator': self.validator,
                'signature': self.signature,
            }
        )
