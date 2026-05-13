from core.base.roi_selector import ROISelector


class StaticROISelector(ROISelector):

    def select_region(self, graph, start, goal, constraints):

        return list(graph.nodes)