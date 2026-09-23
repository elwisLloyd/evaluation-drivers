from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .config import Settings
from .file_io import (
    append_jsonl,
    atomic_write_json,
    case_id_from_path,
    discover_markdown_cases,
    load_catalog,
    read_prompt,
    read_text,
    sha256_text,
)
from .openai_client import StructuredOpenAIClient
from .schemas import CatalogCaseAnalysis, DriverCatalog, utc_now


def _format_user_prompt(template: str, catalog: DriverCatalog, case_id: str, path: Path, text: str) -> str:
    return template.format(
        catalog_json=catalog.model_dump_json(indent=2),
        case_id=case_id,
        case_path=path.as_posix(),
        case_text=text,
    )


def apply_catalog_analysis(
    catalog: DriverCatalog, analysis: CatalogCaseAnalysis, case_id: str
) -> tuple[DriverCatalog, list[dict]]:
    """Apply structurally valid proposals and return the updated catalog plus decisions."""
    updated = deepcopy(catalog)
    by_id = {driver.driver_id: driver for driver in updated.drivers}
    decisions: list[dict] = []
    changed = False

    for proposal in analysis.change_proposals:
        decision = {"action": proposal.action, "accepted": False, "reason": proposal.reason}
        if proposal.action == "add_new_driver" and proposal.candidate_driver:
            candidate = proposal.candidate_driver
            if candidate.driver_id not in by_id and candidate.work_area in updated.work_areas:
                if case_id not in candidate.introduced_by_cases:
                    candidate.introduced_by_cases.append(case_id)
                updated.drivers.append(candidate)
                by_id[candidate.driver_id] = candidate
                decision.update(accepted=True, driver_id=candidate.driver_id)
                changed = True
            else:
                decision["rejection"] = "duplicate driver_id or unknown work_area"
        elif proposal.action == "extend_existing_driver" and proposal.target_driver_id:
            target = by_id.get(proposal.target_driver_id)
            if target:
                known = {category.category_id for category in target.categories}
                additions = [c for c in proposal.categories_to_add if c.category_id not in known]
                target.categories.extend(additions)
                decision.update(accepted=bool(additions), driver_id=target.driver_id)
                changed = changed or bool(additions)
            else:
                decision["rejection"] = "target driver does not exist"
        decisions.append(decision)

    if changed:
        updated.catalog_version += 1
        updated.updated_at = utc_now()
        updated.drivers.sort(key=lambda item: item.driver_id)
    # Re-validation catches overlapping ranges introduced by an extension.
    return DriverCatalog.model_validate(updated.model_dump()), decisions


def run_catalog_build(settings: Settings, client: StructuredOpenAIClient | None = None) -> DriverCatalog:
    client = client or StructuredOpenAIClient(settings)
    catalog = load_catalog(settings.driver_catalog_path)
    system_prompt = read_prompt(settings.prompts_dir, "catalog_case_analysis_system.txt")
    user_template = read_prompt(settings.prompts_dir, "catalog_case_analysis_user.txt")
    output_dir = settings.artifacts_dir / "catalog_build"
    run_id = utc_now().replace(":", "").replace("+00:00", "Z")

    for path in discover_markdown_cases(settings.train_cases_dir):
        case_id = case_id_from_path(path)
        case_text = read_text(path)
        version_before = catalog.catalog_version
        analysis = client.parse(
            system_prompt,
            _format_user_prompt(user_template, catalog, case_id, path, case_text),
            CatalogCaseAnalysis,
        )
        catalog, decisions = apply_catalog_analysis(catalog, analysis, case_id)
        atomic_write_json(settings.driver_catalog_path, catalog)
        append_jsonl(
            output_dir / "case_analysis.jsonl",
            {
                "run_id": run_id,
                "case_id": case_id,
                "case_path": path.as_posix(),
                "input_sha256": sha256_text(case_text),
                "catalog_version_before": version_before,
                "catalog_version_after": catalog.catalog_version,
                "analysis": analysis.model_dump(mode="json"),
                "applied_decisions": decisions,
            },
        )

    snapshot = settings.driver_catalog_path.parent / "history" / f"evaluation_drivers_v{catalog.catalog_version:03d}.json"
    atomic_write_json(snapshot, catalog)
    summary = [
        f"# Catalog build {run_id}",
        "",
        f"- Catalog version: {catalog.catalog_version}",
        f"- Drivers: {len(catalog.drivers)}",
        f"- Train cases: {len(discover_markdown_cases(settings.train_cases_dir))}",
    ]
    (output_dir / "run_summary.md").parent.mkdir(parents=True, exist_ok=True)
    (output_dir / "run_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return catalog
