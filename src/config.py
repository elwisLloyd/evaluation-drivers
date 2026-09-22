from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _as_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    openai_temperature: float
    openai_max_retries: int
    openai_timeout_seconds: int
    train_cases_dir: Path
    test_cases_dir: Path
    artifacts_dir: Path
    driver_catalog_path: Path
    prompts_dir: Path
    probability_sum_tolerance: float
    add_request_min_confidence: float
    auto_apply_min_confidence: float
    catalog_language: str
    log_level: str

    @classmethod
    def from_env(cls, env_file: str | Path = ".env", require_api_key: bool = True) -> "Settings":
        load_dotenv(env_file)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if require_api_key and not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Copy .env.example to .env and add the key.")
        return cls(
            openai_api_key=api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            openai_temperature=_as_float("OPENAI_TEMPERATURE", 0),
            openai_max_retries=_as_int("OPENAI_MAX_RETRIES", 3),
            openai_timeout_seconds=_as_int("OPENAI_TIMEOUT_SECONDS", 120),
            train_cases_dir=Path(os.getenv("TRAIN_CASES_DIR", "data/train")),
            test_cases_dir=Path(os.getenv("TEST_CASES_DIR", "data/test")),
            artifacts_dir=Path(os.getenv("ARTIFACTS_DIR", "artifacts")),
            driver_catalog_path=Path(
                os.getenv("DRIVER_CATALOG_PATH", "artifacts/drivers/evaluation_drivers.json")
            ),
            prompts_dir=Path(os.getenv("PROMPTS_DIR", "prompts")),
            probability_sum_tolerance=_as_float("PROBABILITY_SUM_TOLERANCE", 0.001),
            add_request_min_confidence=_as_float("ADD_REQUEST_MIN_CONFIDENCE", 0.75),
            auto_apply_min_confidence=_as_float("AUTO_APPLY_MIN_CONFIDENCE", 0.90),
            catalog_language=os.getenv("CATALOG_LANGUAGE", "ru"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
