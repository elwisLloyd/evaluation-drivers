from __future__ import annotations

from .schemas import DriverCatalog, DriverInference


def calculate_information_coverage(
    results: list[DriverInference], catalog: DriverCatalog
) -> tuple[float, list[dict[str, float | str]]]:
    """Return weighted basis coverage and the value of clarifying each driver.

    ``cost_impact_percent`` is used as a relative weight.  For each applicable
    driver, the probability assigned to ``unknown`` is treated as its missing
    information fraction.  Consequently, clarifying a driver increases total
    coverage by exactly ``weighted_unknown / total_weight`` percentage points.
    """
    drivers = {driver.driver_id: driver for driver in catalog.drivers}
    applicable = [result for result in results if result.relevance != "not_relevant"]
    total_weight = sum(drivers[result.driver_id].cost_impact_percent for result in applicable)
    if not total_weight:
        return 100.0, []

    rows: list[dict[str, float | str]] = []
    total_missing_weight = 0.0
    for result in applicable:
        driver = drivers[result.driver_id]
        unknown_probability = next(
            (
                value.probability
                for value in result.probability_distribution
                if value.category_id == "unknown"
            ),
            0.0,
        )
        missing_weight = driver.cost_impact_percent * unknown_probability
        total_missing_weight += missing_weight
        rows.append(
            {
                "driver_id": driver.driver_id,
                "driver_name": driver.name,
                "cost_impact_percent": driver.cost_impact_percent,
                "unknown_probability_percent": unknown_probability * 100,
                "coverage_gain_percentage_points": missing_weight / total_weight * 100,
            }
        )

    coverage = (1 - total_missing_weight / total_weight) * 100
    for row in rows:
        gain = float(row["coverage_gain_percentage_points"])
        row["removable_uncertainty_percent"] = (
            gain / (100 - coverage) * 100 if coverage < 100 else 0.0
        )
    rows.sort(key=lambda row: float(row["coverage_gain_percentage_points"]), reverse=True)
    return coverage, rows
