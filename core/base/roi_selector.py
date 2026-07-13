from abc import ABC, abstractmethod


class ROISelector(ABC):
    def __init__(self, scenario):
        self.scenario = scenario
        self.roi_df = None
        self.build_roi()

    @abstractmethod
    def build_roi(self):
        pass