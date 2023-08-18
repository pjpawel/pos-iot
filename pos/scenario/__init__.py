from enum import StrEnum, auto
from threading import Thread

from .definitions import instant_sender, mad_sender, simple_sender
from .exception import ScenarioNotFound, ScenarioNotSupported
from pos.blockchain.blockchain import Node


class Scenario(StrEnum):
    INSTANT_SENDER = auto()
    MAD_SENDER = auto()
    SIMPLE_SENDER = auto()

    def get_definition(self):
        match self:
            case self.INSTANT_SENDER:
                return instant_sender
            case self.MAD_SENDER:
                return mad_sender
            case self.SIMPLE_SENDER:
                return simple_sender
            case _:
                raise ScenarioNotSupported(f"Scenario is not supported: {self.name}")

    def call(self, nodes: list[Node]):
        thread = Thread(target=self.get_definition(), args=[nodes])
        thread.start()


def run_scenarios(names_list: str, nodes):
    """
    Allow to call multiple scenarios
    Pass names as string divided with comma
    :param nodes:
    :param names_list:
    :return:
    """
    names = names_list.split(",")
    for name in names:
        try:
            scenario_enum = getattr(Scenario, name)
        except AttributeError:
            mess = f'Error: There is no scenario with name: {name}'
            print(mess)
            raise ScenarioNotFound(mess)
        scenario_enum.call(nodes)
