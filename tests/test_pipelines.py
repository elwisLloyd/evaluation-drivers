from __future__ import annotations

from shutil import copyfile
from pathlib import Path
from types import SimpleNamespace

from src.catalog_builder import apply_catalog_analysis, run_catalog_build
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


def test_catalog_build_reports_progress_and_skips_failed_case(tmp_path: Path, capsys) -> None:
    cases_dir = tmp_path / "cases"
    prompts_dir = tmp_path / "prompts"
    catalog_path = tmp_path / "drivers" / "catalog.json"
    cases_dir.mkdir()
    prompts_dir.mkdir()
    catalog_path.parent.mkdir()
    (cases_dir / "case_001_first.md").write_text("first", encoding="utf-8")
    (cases_dir / "case_002_second.md").write_text("second", encoding="utf-8")
    (prompts_dir / "catalog_case_analysis_system.txt").write_text("system", encoding="utf-8")
    (prompts_dir / "catalog_case_analysis_user.txt").write_text(
        "{catalog_json}\n{case_id}\n{case_path}\n{case_text}", encoding="utf-8"
    )
    copyfile("artifacts/drivers/evaluation_drivers.json", catalog_path)
    settings = SimpleNamespace(
        train_cases_dir=cases_dir,
        prompts_dir=prompts_dir,
        artifacts_dir=tmp_path / "artifacts",
        driver_catalog_path=catalog_path,
    )

    class Client:
        calls = 0

        def parse(self, *_args):
            self.calls += 1
            if self.calls == 1:
                raise ValueError("broken case")
            return CatalogCaseAnalysis(case_summary="ok", driver_assessments=[], change_proposals=[])

    client = Client()
    catalog = run_catalog_build(settings, client)
    captured = capsys.readouterr()

    assert client.calls == 2
    assert catalog == load_catalog(catalog_path)
    assert "[1/2] ERROR in case_001: ValueError: broken case" in captured.out
    assert "[2/2] Done" in captured.out
    assert "ETA:" in captured.out
    assert "successful: 1 | failed: 1" in captured.out
    assert "ValueError: broken case" in captured.err
    summary = (settings.artifacts_dir / "catalog_build" / "run_summary.md").read_text()
    assert "Successfully processed: 1" in summary
    assert "Failed and skipped: 1" in summary
