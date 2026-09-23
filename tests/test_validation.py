from __future__ import annotations

from pathlib import Path

import pytest

from src.file_io import case_id_from_path, load_catalog
from src.information_coverage import calculate_information_coverage
from src.schemas import DriverCategory, DriverInference, EvaluationDriver, ProbabilityValue
from src.validation import validate_distribution


def test_seed_catalog_is_valid_and_detailed() -> None:
    catalog = load_catalog(Path("artifacts/drivers/evaluation_drivers.json"))
    assert len(catalog.drivers) >= 25
    assert len(catalog.work_areas) >= 20
    assert all(0 < driver.cost_impact_percent <= 100 for driver in catalog.drivers)
    assert all("unknown" in {item.category_id for item in driver.categories} for driver in catalog.drivers)


def test_overlapping_numeric_categories_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        EvaluationDriver(
            driver_id="test.overlap",
            name="test",
            work_area="test",
            source_type="numeric",
            description="test",
            complexity_rationale="test",
            cost_impact_percent=10,
            applicability="test",
            not_applicable_when="test",
            categories=[
                DriverCategory(category_id="low", label="low", lower_bound=0, upper_bound=5),
                DriverCategory(category_id="high", label="high", lower_bound=5, upper_bound=10),
                DriverCategory(category_id="unknown", label="unknown"),
            ],
        )


def test_distribution_validation() -> None:
    catalog = load_catalog(Path("artifacts/drivers/evaluation_drivers.json"))
    driver = catalog.drivers[0]
    result = DriverInference(
        driver_id=driver.driver_id,
        relevance="relevant",
        evidence_status="inferred",
        probability_distribution=[
            ProbabilityValue(category_id=driver.categories[0].category_id, probability=0.7),
            ProbabilityValue(category_id="unknown", probability=0.2),
        ],
        reasoning_summary="test",
    )
    errors = validate_distribution(result, driver, 0.001)
    assert errors == [f"probabilities for {driver.driver_id} sum to 0.900000"]


def test_case_id_extraction() -> None:
    assert case_id_from_path(Path("case_081_long_title.md")) == "case_081"


def test_information_coverage_is_weighted_by_cost_impact() -> None:
    catalog = load_catalog(Path("artifacts/drivers/evaluation_drivers.json"))
    first, second = catalog.drivers[:2]
    results = [
        DriverInference(
            driver_id=driver.driver_id,
            relevance="relevant",
            evidence_status="not_stated",
            probability_distribution=[ProbabilityValue(category_id="unknown", probability=1)],
            reasoning_summary="test",
        )
        for driver in (first, second)
    ]
    coverage, priorities = calculate_information_coverage(results, catalog)
    assert coverage == pytest.approx(0)
    assert priorities[0]["cost_impact_percent"] >= priorities[1]["cost_impact_percent"]
    assert sum(float(row["removable_uncertainty_percent"]) for row in priorities) == pytest.approx(100)
