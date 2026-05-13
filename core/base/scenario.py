from abc import ABC, abstractmethod


class Scenario(ABC):

    @abstractmethod
    def load(self):
        pass