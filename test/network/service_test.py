from uuid import uuid4

from pot.network.service import Node
from pot.network.node import Node as NodeDto
from test.network.conftest import Helper


def test_update_from_validator_single_node(helper: Helper):
    helper.put_storage_env()
    service = Node()

    identifier = uuid4()
    service.update_from_json([{
        "identifier": identifier.hex,
        "host": "localhost",
        "port": 5000,
        "type": "VALIDATOR",
        "trust": 100
    }])

    assert len(service.all()) == 1
    #assert service.count_validator_nodes() == 1
    assert service.find_by_identifier(identifier) is not None
    assert service.find_by_identifier(identifier) == NodeDto(identifier, "localhost", 5000)
    assert service.node_trust.get_node_trust(service.find_by_identifier(identifier)) == 100
    #assert service.validators.all() == [identifier]


def test_update_from_validator(helper: Helper):
    helper.put_storage_env()
    service = Node()

    node = NodeDto(uuid4(), "localhost", 5000)
    service.add(node)

    service.update_from_json([
        {
            "identifier": uuid4().hex,
            "host": "172.0.0.1",
            "port": 5000,
            "type": "VALIDATOR",
            "trust": 100
        },
        {
            "identifier": uuid4().hex,
            "host": "172.0.0.2",
            "port": 5000,
            "type": "SENSOR",
            "trust": 600
        }
    ])

    assert len(service.all()) == 3
    #assert service.count_validator_nodes() == 1


def test_prepare_nodes_info(helper: Helper):
    helper.put_storage_env()
    service = Node()

    identifier1 = uuid4()
    node = NodeDto(identifier1, "172.0.0.1", 5000)
    service.add(node)

    identifier2 = uuid4()
    node = NodeDto(identifier2, "172.0.0.2", 5000)
    service.add(node)

    service.validators.set_validators([identifier1])
    service.node_trust.add_trust_to_node(service.find_by_identifier(identifier1), 300)

    info = [
        {
            "identifier": identifier1.hex,
            "host": "172.0.0.1",
            "port": 5000,
            "type": "VALIDATOR",
            "trust": 600
        },
        {
            "identifier": identifier2.hex,
            "host": "172.0.0.2",
            "port": 5000,
            "type": "SENSOR",
            "trust": 300
        }
    ]
    assert service.prepare_nodes_info(service.all()) == info


def test_node_trust_change(helper: Helper):
    helper.put_storage_env()
    service = Node()

    identifier = uuid4()
    node = NodeDto(identifier, "172.0.0.1", 5000)

    service.node_trust.add_new_node_trust(node)
    basic_trust = service.node_trust.BASIC_TRUST
    assert basic_trust == service.node_trust.get_node_trust(node)

    service.node_trust.add_trust_to_node(node, 20)
    assert basic_trust + 20 == service.node_trust.get_node_trust(node)

    service.node_trust.add_trust_to_node(node, -40)
    assert basic_trust + 20 - 40 == service.node_trust.get_node_trust(node)


def test_update_node(helper: Helper):
    helper.put_storage_env()
    service = Node()

    identifier1 = uuid4()
    node = NodeDto(identifier1, "172.0.0.1", 5000)
    service.add(node)

    identifier2 = uuid4()
    node = NodeDto(identifier2, "172.0.0.2", 5000)
    service.add(node)

    service.validators.set_validators([identifier1])
    service.node_trust.add_new_node_trust(service.find_by_identifier(identifier1), 300)

    identifier3 = uuid4()
    identifier4 = uuid4()
    info = [
        {
            "identifier": identifier3.hex,
            "host": "172.0.0.3",
            "port": 5000,
            "type": "VALIDATOR",
            "trust": 500
        },
        {
            "identifier": identifier4.hex,
            "host": "172.0.0.4",
            "port": 5000,
            "type": "SENSOR",
            "trust": 100
        }
    ]
    service.update_from_json(info)

    assert len(service.all()) == 4
    #assert service.count_validator_nodes() == 1
