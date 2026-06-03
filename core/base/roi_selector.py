from abc import ABC, abstractmethod
from typing import Dict, Any


class ROISelector(ABC):
    def __init__(self, scenario):
        self.scenario = scenario
        self.roi_df = None
        self.build_roi()

    @abstractmethod
    def build_roi(self):
        pass