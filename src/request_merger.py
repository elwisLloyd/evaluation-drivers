from __future__ import annotations

from copy import deepcopy
from typing import Literal

from .config import Settings
from .file_io import append_jsonl, atomic_write_json, load_catalog, load_jsonl, read_prompt
from .openai_client import StructuredOpenAIClient
from .schemas import AddRequest, DriverCatalog, MergeDecision, utc_now


def apply_merge_decision(
    catalog: DriverCatalog,
    request: AddRequest,
    decision: MergeDecision,
    mode: Literal["review", "auto"],
    auto_threshold: float,
) -> tuple[DriverCatalog, str]:
    if mode == "review":
        return catalog, "needs_review"
    if decision.confidence < auto_threshold:
        return catalog, "needs_review"

    updated = deepcopy(catalog)
    by_id = {driver.driver_id: driver for driver in updated.drivers}
    changed = False
    status = "rejected"
    if decision.decision == "accept_new_driver" and decision.normalized_driver:
        driver = decision.normalized_driver
        if driver.driver_id not in by_id and driver.work_area in updated.work_areas:
            updated.drivers.append(driver)
            changed = True
            status = "accepted"
    elif decision.decision == "extend_existing_driver" and decision.target_driver_id in by_id:
        target = by_id[decision.target_driver_id]
        known = {item.category_id for item in target.categories}
        additions = [item for item in decision.categories_to_add if item.category_id not in known]
        target.categories.extend(additions)
        changed = bool(additions)
        status = "accepted" if changed else "rejected"
    elif decision.decision == "needs_human_review":
        status = "needs_review"

    if changed:
        updated.catalog_version += 1
        updated.updated_at = utc_now()
        updated.drivers.sort(key=lambda item: item.driver_id)
    return DriverCatalog.model_validate(updated.model_dump()), status


def run_request_merge(
    settings: Settings,
    mode: Literal["review", "auto"] = "review",
    client: StructuredOpenAIClient | None = None,
) -> DriverCatalog:
    client = client or StructuredOpenAIClient(settings)
    catalog = load_catalog(settings.driver_catalog_path)
    requests_path = settings.artifacts_dir / "inference" / "add_requests.jsonl"
    raw_requests = load_jsonl(requests_path)
    decisions_path = settings.artifacts_dir / "merge" / "merge_decisions.jsonl"
    resolved_ids = {
        item["request"]["request_id"]
        for item in load_jsonl(decisions_path)
        if item.get("application_status") in {"accepted", "rejected"}
    }
    requests = [
        AddRequest.model_validate(item)
        for item in raw_requests
        if item.get("status") == "pending" and item.get("request_id") not in resolved_ids
    ]
    system_prompt = read_prompt(settings.prompts_dir, "merge_requests_system.txt")
    user_template = read_prompt(settings.prompts_dir, "merge_requests_user.txt")
    output_dir = settings.artifacts_dir / "merge"
    run_id = utc_now().replace(":", "").replace("+00:00", "Z")

    for request in requests:
        decision = client.parse(
            system_prompt,
            user_template.format(
                catalog_json=catalog.model_dump_json(indent=2),
                request_json=request.model_dump_json(indent=2),
            ),
            MergeDecision,
        )
        if decision.request_id != request.request_id:
            raise ValueError("Merge decision request_id does not match the request")
        version_before = catalog.catalog_version
        catalog, status = apply_merge_decision(
            catalog, request, decision, mode, settings.auto_apply_min_confidence
        )
        append_jsonl(
            output_dir / "merge_decisions.jsonl",
            {
                "run_id": run_id,
                "mode": mode,
                "catalog_version_before": version_before,
                "catalog_version_after": catalog.catalog_version,
                "request": request.model_dump(mode="json"),
                "decision": decision.model_dump(mode="json"),
                "application_status": status,
            },
        )

    atomic_write_json(settings.driver_catalog_path, catalog)
    snapshot = settings.driver_catalog_path.parent / "history" / f"evaluation_drivers_v{catalog.catalog_version:03d}.json"
    atomic_write_json(snapshot, catalog)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "merge_summary.md").write_text(
        f"# Request merge {run_id}\n\n- Mode: {mode}\n- Requests: {len(requests)}\n"
        f"- Catalog version: {catalog.catalog_version}\n",
        encoding="utf-8",
    )
    return catalog
