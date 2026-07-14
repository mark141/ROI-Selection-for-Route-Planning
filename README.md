# ROI-Selection-for-Route-Planning

## Thesis: Adaptive Region of Interest Selection Under Dynamic Constraints for Efficient Route Planning

### Abstract:

Dynamic weather conditions can significantly affect route planning, yet many existing approaches rely on
computationally intensive methods or large datasets. This thesis presents a lightweight preprocessing method for 
adaptive region of interest (ROI) selection using precipitation forecasts. Starting from predefined baseline shapes, 
the approach identifies suitable departure time windows and iteratively refines the search region by applying 
decreasing precipitation thresholds while preserving spatial connectivity. The resulting ROI highlights 
weather-favorable areas that can be supplied to existing routing APIs to reduce exposure to rainfall. By relying solely
on weather forecast data, the proposed method remains computationally efficient, independent of historical data, and 
easily adaptable as a preprocessing step for weather-aware route planning.


## Project Structure
```
ROI-Selection-for-Route-Planning
│
├── README.md
├── requirements.txt
├── pyproject.toml
│
├── core/
│   ├── __init__.py
│   │
│   ├── interfaces/
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
│   └── scenarios.py
│
└──  tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_constraints.py
    ├── test_roi.py
    ├── test_planner.py
    └── test_simulation.py
```
# Installation

The project uses **Poetry** for dependency management and virtual environment handling.

## 1. Install Poetry

Follow the official installation guide:

https://python-poetry.org/docs/


Verify the installation:

```bash
poetry --version
```

## 2. Clone the Repository

```bash
git clone https://github.com/mark141/ROI-Selection-for-Route-Planning.git
cd ROI-Selection-for-Route-Planning
```

## 3. Install Dependencies

Poetry automatically creates a virtual environment and installs all required packages defined in `pyproject.toml`.

```bash
poetry install
```

## 4. Configure API Keys

Some functionality requires API credentials.

Create the file

```
utils/config.py
```

and provide the required configuration values, for example:

```python
ORS_API_KEY = "YOUR_OPENROUTESERVICE_KEY"
```

The weather data is retrieved from the Open-Meteo API and does **not** require an API key.

## 6. Running an Example

The example scenarios used in the thesis can be individually imported and executed directly from Python.


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
```

## Limitations

This project relies on the Open-Meteo Historical Forecast API for retrieving weather forecast data.

- Historical forecast data is only available for a limited time window. At the time of implementation, requests are restricted to approximately **3 months before the current date** and **15 days after the current date**.
- As a result, arbitrary historical experiments cannot be reproduced once the requested time period falls outside the API's supported range.
- The weather data represents gridded numerical weather model output rather than observations from local weather stations. Consequently, localized weather phenomena may not be captured accurately.

For unrestricted long-term historical analyses, the Open-Meteo Historical Weather API or another historical weather dataset should be used instead of the Historical Forecast API.