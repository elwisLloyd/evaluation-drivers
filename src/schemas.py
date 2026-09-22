from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceType(str, Enum):
    numeric = "numeric"
    categorical = "categorical"
    binary = "binary"


class DriverCategory(StrictModel):
    category_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    description: str = ""
    lower_bound: float | None = None
    upper_bound: float | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = True

    @model_validator(mode="after")
    def bounds_are_ordered(self) -> "DriverCategory":
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound > self.upper_bound
        ):
            raise ValueError("lower_bound must not exceed upper_bound")
        return self


class EvaluationDriver(StrictModel):
    driver_id: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    name: str
    work_area: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    source_type: SourceType
    unit: str | None = None
    description: str
    complexity_rationale: str
    applicability: str
    not_applicable_when: str
    categories: list[DriverCategory] = Field(min_length=2)
    selection_guidance: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    status: Literal["active", "deprecated"] = "active"
    introduced_by_cases: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def categories_are_valid(self) -> "EvaluationDriver":
        ids = [item.category_id for item in self.categories]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate category_id in {self.driver_id}")
        if "unknown" not in ids:
            raise ValueError(f"{self.driver_id} must contain an unknown category")
        if self.source_type == SourceType.numeric:
            bounded = [c for c in self.categories if c.category_id != "unknown"]
            ordered = sorted(
                bounded,
                key=lambda c: float("-inf") if c.lower_bound is None else c.lower_bound,
            )
            for left, right in zip(ordered, ordered[1:]):
                if left.upper_bound is None:
                    raise ValueError(f"open upper bound overlaps later category in {self.driver_id}")
                if right.lower_bound is None:
                    raise ValueError(f"open lower bound overlaps earlier category in {self.driver_id}")
                if left.upper_bound > right.lower_bound:
                    raise ValueError(f"numeric ranges overlap in {self.driver_id}")
                if (
                    left.upper_bound == right.lower_bound
                    and left.upper_inclusive
                    and right.lower_inclusive
                ):
                    raise ValueError(f"numeric ranges overlap at boundary in {self.driver_id}")
        return self


class DriverCatalog(StrictModel):
    schema_version: str = "1.0"
    catalog_version: int = Field(ge=1)
    catalog_id: str
    title: str
    description: str
    language: str = "ru"
    created_at: str
    updated_at: str
    work_areas: list[str]
    drivers: list[EvaluationDriver]

    @model_validator(mode="after")
    def driver_ids_are_unique(self) -> "DriverCatalog":
        ids = [driver.driver_id for driver in self.drivers]
        if len(ids) != len(set(ids)):
            raise ValueError("driver_id values must be unique")
        unknown_areas = {driver.work_area for driver in self.drivers} - set(self.work_areas)
        if unknown_areas:
            raise ValueError(f"unknown work areas: {sorted(unknown_areas)}")
        return self


class Evidence(StrictModel):
    quote: str
    location_hint: str


class ExistingDriverAssessment(StrictModel):
    driver_id: str
    decision: Literal["relevant", "not_relevant", "insufficient_context"]
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)


class CatalogChangeProposal(StrictModel):
    action: Literal["extend_existing_driver", "add_new_driver", "no_change"]
    target_driver_id: str | None = None
    candidate_driver: EvaluationDriver | None = None
    categories_to_add: list[DriverCategory] = Field(default_factory=list)
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class CatalogCaseAnalysis(StrictModel):
    case_summary: str
    driver_assessments: list[ExistingDriverAssessment]
    change_proposals: list[CatalogChangeProposal]
    uncovered_work_areas: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProbabilityValue(StrictModel):
    category_id: str
    probability: float = Field(ge=0, le=1)


class DriverInference(StrictModel):
    driver_id: str
    relevance: Literal["relevant", "not_relevant", "insufficient_context"]
    evidence_status: Literal["explicit", "inferred", "not_stated", "contradictory"]
    probability_distribution: list[ProbabilityValue] = Field(default_factory=list)
    reasoning_summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)


class AddRequest(StrictModel):
    request_id: str = "pending"
    created_at: str = Field(default_factory=utc_now)
    source_case_id: str
    source_case_path: str
    catalog_version: int = Field(ge=1)
    request_type: Literal["new_driver", "new_category", "clarify_driver_definition"]
    target_driver_id: str | None = None
    candidate_driver: EvaluationDriver | None = None
    categories_to_add: list[DriverCategory] = Field(default_factory=list)
    gap_description: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    status: Literal["pending", "accepted", "rejected", "needs_review"] = "pending"


class AddRequestDraft(StrictModel):
    request_type: Literal["new_driver", "new_category", "clarify_driver_definition"]
    target_driver_id: str | None = None
    candidate_driver: EvaluationDriver | None = None
    categories_to_add: list[DriverCategory] = Field(default_factory=list)
    gap_description: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class CaseInferenceResponse(StrictModel):
    case_summary: str
    driver_results: list[DriverInference]
    add_requests: list[AddRequestDraft] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MergeDecision(StrictModel):
    request_id: str
    decision: Literal[
        "accept_new_driver",
        "extend_existing_driver",
        "reject_duplicate",
        "reject_not_a_driver",
        "needs_human_review",
    ]
    target_driver_id: str | None = None
    normalized_driver: EvaluationDriver | None = None
    categories_to_add: list[DriverCategory] = Field(default_factory=list)
    reason: str
    confidence: float = Field(ge=0, le=1)
