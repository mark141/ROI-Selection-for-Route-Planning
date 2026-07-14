from dataclasses import dataclass
from time import perf_counter
from shapely.geometry import Polygon


@dataclass
class EvaluationResult:
    scenario: str

    # -----------------------------
    # Runtime
    # -----------------------------
    roi_creation_time: float
    weather_request_time: float
    iteration_time: float
    total_runtime: float

    # -----------------------------
    # ROI metrics
    # -----------------------------
    initial_area: float
    final_area: float
    roi_reduction: float
    remaining_area: float

    # -----------------------------
    # Constraint metrics
    # (evaluated on reachable_df only)
    # -----------------------------
    reachable_points: int
    satisfying_points: int
    violating_points: int
    constraint_satisfaction: float

    # -----------------------------
    # Iteration metrics
    # -----------------------------
    iterations: int
    final_threshold: float
    holes: int

    # Connectivity is guaranteed by construction.
    # This flag is mainly included for completeness.
    connected: bool

    departure_time: str


    def print_summary(self):

        print("\n" + "=" * 70)
        print(f"Evaluation Summary - {self.scenario}")
        print("=" * 70)

        print("\nROI")
        print("-" * 70)
        print(f"Initial Area           : {self.initial_area:.2f}")
        print(f"Final Area             : {self.final_area:.2f}")
        print(f"Area Reduction         : {self.roi_reduction:.2%}")
        print(f"Remaining Search Space : {self.remaining_area:.2%}")

        print("\nConstraint Satisfaction")
        print("-" * 70)
        print(f"Reachable Points       : {self.reachable_points}")
        print(f"Satisfying Points      : {self.satisfying_points}")
        print(f"Violating Points       : {self.violating_points}")
        print(f"Satisfaction Ratio     : {self.constraint_satisfaction:.2%}")

        print("\nIteration")
        print("-" * 70)
        print(f"Iterations             : {self.iterations}")
        print(f"Final Threshold        : {self.final_threshold:.2f} mm")
        print(f"Interior Holes         : {self.holes}")
        print(f"Connected              : {'Yes' if self.connected else 'No'}")

        print("\nRuntime")
        print("-" * 70)
        print(f"ROI Creation           : {self.roi_creation_time:.3f} s")
        print(f"Weather API            : {self.weather_request_time:.3f} s")
        print(f"ROI Iteration          : {self.iteration_time:.3f} s")
        print(f"Total Runtime          : {self.total_runtime:.3f} s")

        print("\nDeparture Time")
        print("-" * 70)
        print(self.departure_time)

        print("=" * 70 + "\n")

    @staticmethod
    def print_summary_different_departure(selected_departure, best_departure, selected_precipitation, best_precipitation, departure_selection_accuracy):
        print("\n" + "=" * 70)
        print(f"Evaluation Summary - Different Departure")
        print("=" * 70)

        print("\nDeparture Optimization")
        print("-" * 70)
        print(f"Selected Departure           : {selected_departure}")
        print(f"Best Departure               : {best_departure}")

        print(f"\nSelected Precipitation     : {selected_precipitation:.1f} mm")
        print(f"Minimum Precipitation        : {best_precipitation:.1f} mm")

        print(f"\nSelected Accuracy          : {departure_selection_accuracy:.2%}")

        print(f"\nImprovement over initial:\n")
        print(f"{(1 - departure_selection_accuracy ):.2%}")




class Timer:

    def __init__(self):
        self.start = perf_counter()

    def stop(self):
        return perf_counter() - self.start