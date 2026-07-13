# ROI-Selection-for-Route-Planning

## Thesis: Adaptive Region of Interest Selection Under Dynamic Constraints for Efficient Route Planning

### Abstract:

This thesis presents a constraint-aware region of interest (ROI) selection method to improve 
the efficiency and reliability of route planning. The approach incorporates dynamic environmental
factors, using weather conditions as a representative example to demonstrate its extensibility
to additional constraints. Unlike traditional methods that rely on fixed ROIs, the proposed
approach dynamically adapts the search region based on real-time data. This enables the system
to prioritize relevant areas while avoiding constraint-violating regions. The work focuses 
on the design of adaptive ROI heuristics and their evaluation across diverse scenarios. A full 
implementation of the method is provided. Its effectiveness is demonstrated through simulation 
and performance analysis.


## Project Structure
```
ROI-Selection-for-Route-Planning
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── main.py
│
├── core/
│   ├── __init__.py
│   │
│   ├── base/
│   │   ├── __init__.py
│   │   ├── roi_selector.py
│   │   ├── constraint.py
│   │   ├── planner.py
│   │   └── scenario.py
│   │
│   ├── roi/
│   │   ├── __init__.py
│   │   ├── roi.py
│   │   └── roi_iterator.py
│   │
│   ├── constraints/
│   │   ├── __init__.py
│   │   ├── weather_constraint.py
│   │   ├── traffic_constraint.py
│   │   └── energy_constraint.py
│   │
│   ├── planning/
│   │   ├── __init__.py
│   │   ├── astar.py
│   │   ├── dijkstra.py
│   │   └── route_manager.py
│   │
│   └── simulation/
│       ├── __init__.py
│       ├── simulator.py
│       ├── evaluator.py
│       └── metrics.py
│
├── utils/
│   ├── __init__.py
│   ├── config.py
│   ├── dates.py
│   ├── geometry.py
│   ├── graph_utils.py
│   └── visualization.py
│
├── data/
│   ├── maps/
│   ├── weather/
│   └── scenarios/
│
├── experiments/
│   ├── benchmark_01.py
│   ├── benchmark_02.py
│   └── compare_roi_methods.py
│
└──  tests/
    ├── __init__.py
    │
    ├── conftest.py
    ├── test_constraints.py
    ├── test_roi.py
    ├── test_planner.py
    └── test_simulation.py
```

## Usage Example

The following example demonstrates the complete workflow of the adaptive ROI generation process.

The library follows these main steps:

1. Define a routing scenario (start, destination, and constraints)
2. Generate an initial region of interest (ROI) using a baseline shape
3. Retrieve weather data for the initial ROI
4. Iteratively refine the ROI based on precipitation constraints
5. Export the resulting ROI for use with routing APIs or further processing

### Example

```python
import pandas as pd

from core.constraints.weather_constraint import WeatherConstraint
from core.roi.roi import ROISelectorFactory
from core.base.scenario import Scenario
from core.roi.roi_iterator import ROIIterator
from utils.geometry import to_simple_polygon


# Define start and destination coordinates
start = (52.5200, 13.4050)  # Berlin
goal = (48.8566, 2.3522)    # Paris

# Define desired departure time
departure_time = pd.Timestamp("2026-07-06 08:00")


# Define dynamic constraints
constraints = {
    # Maximum allowed precipitation in mm
    "max_rain": 1.5,

    # Weather forecast timeframe
    "start_date": "2026-07-06",
    "end_date": "2026-07-08",

    # Additional safety buffer
    "buffer": 0.05,

    # ROI optimization mode
    # "departure" optimizes the region based on the departure timeframe
    "mode": "departure",

    "departure_time": departure_time,
}


# Create scenario configuration
scenario = Scenario(
    start=start,
    goal=goal,
    constraints=constraints
)


# Generate initial ROI
#
# The initial ROI defines the search area where weather data is collected.
# Available baseline shapes can be selected through ROISelectorFactory.
initial_roi = ROISelectorFactory.create(
    scenario,
    "BBox"
)


# Fetch weather information for the initial region
weather_constraint = WeatherConstraint()

weather_constraint.fetch_weather(
    grid_df=initial_roi.roi_df,
    start_date=scenario.constraints["start_date"],
    end_date=scenario.constraints["end_date"]
)


# Create ROI iterator
#
# The iterator progressively reduces the precipitation threshold while
# maintaining a connected region.
roi_iterator = ROIIterator(
    initial_roi=initial_roi,
    constraints={
        "weather_constraint": weather_constraint
    },
    scenario=scenario,
    mode=scenario.constraints["mode"]
)


# Run ROI refinement iterations
#
# Each iteration reduces the allowed precipitation threshold and stores
# the intermediate results.
roi = roi_iterator.run_iterations(n=10)


# Convert ROI into a simple polygon representation
# suitable for external routing APIs
if roi.interiors:
    roi = to_simple_polygon(roi)