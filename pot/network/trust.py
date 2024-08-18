from enum import IntEnum
from uuid import UUID


class TrustChangeType(IntEnum):
    BLOCK_VALIDATED = 10

    TRANSACTION_VALIDATED = 1


class NodeTrustChange:
    node_id: UUID
    timestamp: int
    type: TrustChangeType
    change: int

    def __init__(self, node_id: UUID, timestamp: int, change_type: TrustChangeType, change: int):
        self.node_id = node_id
        self.timestamp = timestamp
        self.type = change_type
        self.change = change

    def to_list(self) -> list:
        return [self.node_id.hex, self.timestamp, self.type.value, self.change]

    @classmethod
    def load_from_list(cls, data: list):
        node_id = UUID(data[0])
        change_type = TrustChangeType(int(data[2]))
        return cls(node_id, int(data[1]), change_type, int(data[3]))
