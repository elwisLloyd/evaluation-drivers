from __future__ import annotations

import json
from pathlib import Path

from .config import Settings
from .file_io import (
    append_jsonl,
    case_id_from_path,
    load_catalog,
    read_prompt,
    read_text,
    sha256_text,
    write_csv,
)
from .openai_client import StructuredOpenAIClient
from .schemas import AddRequest, CaseInferenceResponse, utc_now
from .validation import validate_inference_results


def _request_id(run_id: str, case_id: str, index: int) -> str:
    safe_run_id = "".join(character for character in run_id if character.isalnum())
    return f"req_{safe_run_id}_{case_id}_{index:03d}"


def run_inference(
    settings: Settings, case_filename: str, client: StructuredOpenAIClient | None = None
) -> list[dict]:
    client = client or StructuredOpenAIClient(settings)
    catalog = load_catalog(settings.driver_catalog_path)
    system_prompt = read_prompt(settings.prompts_dir, "inference_system.txt")
    user_template = read_prompt(settings.prompts_dir, "inference_user.txt")
    output_dir = settings.artifacts_dir / "inference"
    run_id = utc_now().replace(":", "").replace("+00:00", "Z")
    detailed: list[dict] = []
    compact_rows: list[dict] = []

    if Path(case_filename).name != case_filename or not case_filename.endswith(".md"):
        raise ValueError("case_filename must be the name of a Markdown file, without directories")
    path = settings.test_cases_dir / case_filename
    if not path.is_file():
        raise FileNotFoundError(f"Test case does not exist: {path}")

    for path in [path]:
        case_id = case_id_from_path(path)
        case_text = read_text(path)
        user_prompt = user_template.format(
            catalog_json=catalog.model_dump_json(indent=2),
            case_id=case_id,
            case_path=path.as_posix(),
            case_text=case_text,
        )
        response = client.parse(system_prompt, user_prompt, CaseInferenceResponse)
        errors = validate_inference_results(
            response.driver_results, catalog, settings.probability_sum_tolerance
        )
        if errors:
            raise ValueError(f"Invalid inference for {case_id}: {'; '.join(errors)}")

        requests: list[AddRequest] = []
        for index, draft in enumerate(response.add_requests, start=1):
            if draft.confidence < settings.add_request_min_confidence:
                continue
            request = AddRequest(
                request_id=_request_id(run_id, case_id, index),
                source_case_id=case_id,
                source_case_path=path.as_posix(),
                catalog_version=catalog.catalog_version,
                **draft.model_dump(),
            )
            requests.append(request)
            append_jsonl(output_dir / "add_requests.jsonl", request)

        record = {
            "run_id": run_id,
            "case_id": case_id,
            "case_path": path.as_posix(),
            "input_sha256": sha256_text(case_text),
            "catalog_version": catalog.catalog_version,
            "model": settings.openai_model,
            "temperature": settings.openai_temperature,
            "case_summary": response.case_summary,
            "driver_results": [item.model_dump(mode="json") for item in response.driver_results],
            "add_request_ids": [item.request_id for item in requests],
            "warnings": response.warnings,
        }
        detailed.append(record)
        append_jsonl(output_dir / "detailed_results.jsonl", record)

        compact_values: dict[str, dict[str, float]] = {}
        for result in response.driver_results:
            if result.relevance == "not_relevant":
                continue
            distribution = {item.category_id: item.probability for item in result.probability_distribution}
            compact_values[result.driver_id] = distribution
            top_category, top_probability = max(distribution.items(), key=lambda item: item[1])
            compact_rows.append(
                {
                    "case_id": case_id,
                    "driver_id": result.driver_id,
                    "relevance": result.relevance,
                    "evidence_status": result.evidence_status,
                    "top_category": top_category,
                    "top_probability": top_probability,
                    "distribution": json.dumps(distribution, ensure_ascii=False, sort_keys=True),
                }
            )
        append_jsonl(output_dir / "compact_results.jsonl", {"case_id": case_id, "values": compact_values})

    write_csv(
        output_dir / "compact_results.csv",
        compact_rows,
        [
            "case_id",
            "driver_id",
            "relevance",
            "evidence_status",
            "top_category",
            "top_probability",
            "distribution",
        ],
    )
    (output_dir / "run_summary.md").write_text(
        f"# Inference {run_id}\n\n- Cases: {len(detailed)}\n- Catalog version: {catalog.catalog_version}\n"
        f"- Compact values: {len(compact_rows)}\n",
        encoding="utf-8",
    )
    return detailed
