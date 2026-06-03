from typing import Dict, Any, List

from core.base.roi_selector import ROISelector
from utils.geometry import interpolate_points


class DynamicROISelector(ROISelector):

    def __init__(self, constraints: List):
        self.constraints = constraints

    def generate(self, scenario):

        sampled_points = interpolate_points(
            scenario.start,
            scenario.goal,
            steps=100
        )

        valid_points = []

        logs = []

        for point in sampled_points:

            point_valid = True
            total_cost = 0 # TODO: macht keinen sinn hier
            point_meta = {}

            # TODO: ANDERES SETUP HIER
            #  Weather Constraints als liste durchgehen? das mache ich hier grade
            #  Oder die angegebenen Constraints als ganzes ansehen?
            #  Grid erstellen/nehmen -> Weather Fetchen ->
            #  Quick Return ??
            #  -> iterieren bis ROI passt
            for constraint in self.constraints:

                result = constraint.evaluate(
                    point,
                    scenario.constraints
                )

                total_cost += result["cost"]

                point_meta[constraint.__class__.__name__] = result

                if not result["valid"]:
                    point_valid = False

            logs.append({
                "point": point,
                "valid": point_valid,
                "cost": total_cost,
                "meta": point_meta
            })

            if point_valid:
                valid_points.append(point)

        roi = self._build_roi(valid_points)

        return {
            "roi": roi,
            "log": logs
        }

    def _build_roi(self, valid_points):

        if not valid_points:
            return None

        lats = [p[0] for p in valid_points]
        lons = [p[1] for p in valid_points]

        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
            "points": valid_points
        }