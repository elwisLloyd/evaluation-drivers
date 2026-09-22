from __future__ import annotations

from collections import Counter

from .schemas import DriverCatalog, DriverInference, EvaluationDriver


def validate_distribution(
    result: DriverInference,
    driver: EvaluationDriver,
    tolerance: float,
) -> list[str]:
    errors: list[str] = []
    allowed = {category.category_id for category in driver.categories}
    provided = [item.category_id for item in result.probability_distribution]
    unknown = set(provided) - allowed
    if unknown:
        errors.append(f"unknown categories for {driver.driver_id}: {sorted(unknown)}")
    duplicates = [key for key, count in Counter(provided).items() if count > 1]
    if duplicates:
        errors.append(f"duplicate categories for {driver.driver_id}: {duplicates}")
    if result.relevance == "not_relevant" and provided:
        errors.append(f"not_relevant driver {driver.driver_id} must have no distribution")
    if result.relevance != "not_relevant":
        if not provided:
            errors.append(f"{driver.driver_id} has no probability distribution")
        probability_sum = sum(item.probability for item in result.probability_distribution)
        if abs(probability_sum - 1.0) > tolerance:
            errors.append(f"probabilities for {driver.driver_id} sum to {probability_sum:.6f}")
    return errors


def validate_inference_results(
    results: list[DriverInference], catalog: DriverCatalog, tolerance: float
) -> list[str]:
    errors: list[str] = []
    by_id = {driver.driver_id: driver for driver in catalog.drivers}
    seen: set[str] = set()
    for result in results:
        if result.driver_id in seen:
            errors.append(f"duplicate driver result: {result.driver_id}")
            continue
        seen.add(result.driver_id)
        driver = by_id.get(result.driver_id)
        if driver is None:
            errors.append(f"unknown driver: {result.driver_id}")
            continue
        errors.extend(validate_distribution(result, driver, tolerance))
    return errors
