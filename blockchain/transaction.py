import json


class Transaction:
    source_id: str
    signature: str
    data: dict

    def __init__(self):
        pass

    def to_json(self) -> str:
        return json.dumps(
            {
                'source_id': self.source_id,
                'signature': self.signature,
                'data': self.data,
            }
        )


class TransactionService:
    pass
