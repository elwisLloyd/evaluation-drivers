from __future__ import annotations

from pathlib import Path

from src.catalog_builder import apply_catalog_analysis
from src.file_io import load_catalog
from src.request_merger import apply_merge_decision
from src.schemas import (
    AddRequest,
    CatalogCaseAnalysis,
    CatalogChangeProposal,
    DriverCategory,
    MergeDecision,
)


def test_catalog_extension_increments_version() -> None:
    catalog = load_catalog(Path("artifacts/drivers/evaluation_drivers.json"))
    target = catalog.drivers[0]
    analysis = CatalogCaseAnalysis(
        case_summary="test",
        driver_assessments=[],
        change_proposals=[
            CatalogChangeProposal(
                action="extend_existing_driver",
                target_driver_id=target.driver_id,
                categories_to_add=[DriverCategory(category_id="test_value", label="Test")],
                reason="test",
                confidence=1,
            )
        ],
    )
    updated, decisions = apply_catalog_analysis(catalog, analysis, "case_test")
    assert updated.catalog_version == catalog.catalog_version + 1
    assert decisions[0]["accepted"] is True


def test_review_mode_never_changes_catalog() -> None:
    catalog = load_catalog(Path("artifacts/drivers/evaluation_drivers.json"))
    request = AddRequest(
        source_case_id="case_test",
        source_case_path="case.md",
        catalog_version=catalog.catalog_version,
        request_type="new_category",
        target_driver_id=catalog.drivers[0].driver_id,
        gap_description="test",
        confidence=1,
    )
    decision = MergeDecision(
        request_id=request.request_id,
        decision="extend_existing_driver",
        target_driver_id=catalog.drivers[0].driver_id,
        categories_to_add=[DriverCategory(category_id="test_value", label="Test")],
        reason="test",
        confidence=1,
    )
    updated, status = apply_merge_decision(catalog, request, decision, "review", 0.9)
    assert updated == catalog
    assert status == "needs_review"
