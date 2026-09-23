# Evaluation drivers

MVP для построения категориального базиса драйверов сложности ML/AI-проектов и разложения текстовых кейсов по этому базису. Драйверы описывают объём и характер работ; экспертный вес `cost_impact_percent` показывает, какую долю стоимости может определять драйвер, но не является сметой.

## Состав

1. `notebooks/01_build_driver_catalog.ipynb` — анализирует `data/train/*.md`, сопоставляет кейсы с каталогом и дополняет его.
2. `notebooks/02_infer_case_drivers.ipynb` — анализирует один указанный файл из `data/test`, формирует распределения по категориям, оценивает полноту и ранжирует уточнения.
3. `notebooks/03_apply_add_requests.ipynb` — проверяет requests to add и применяет их в `review` или `auto` режиме.

Общая реализация находится в `src/`, промпты — в `prompts/`, канонический seed-каталог — в `artifacts/drivers/evaluation_drivers.json`. Seed-каталог намеренно широк: он покрывает данные, моделирование, интеграции, serving, безопасность и эксплуатацию, после чего notebook 1 уточняет его на обучающих кейсах.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Заполните OPENAI_API_KEY и при необходимости OPENAI_MODEL в .env
jupyter notebook
```

Ноутбуки нужно запускать по порядку. Все пути и параметры OpenAI читаются из `.env`. Ключ API не должен попадать в notebook или Git.

## Артефакты

- `artifacts/drivers/evaluation_drivers.json` — текущая версия каталога;
- `artifacts/drivers/history/` — snapshots каталога;
- `artifacts/catalog_build/case_analysis.jsonl` — подробный журнал построения;
- `artifacts/inference/detailed_results.jsonl` — evidence, объяснения и полные распределения;
- `artifacts/inference/compact_results.csv` и `.jsonl` — компактные значения;
- `artifacts/inference/add_requests.jsonl` — запросы на расширение базиса;
- `artifacts/merge/merge_decisions.jsonl` — решения по запросам.

JSONL-файлы дописываются между запусками и содержат `run_id`. Перед чистым экспериментом их можно удалить.

## Семантика результата

- `source_type` (`numeric`, `categorical`, `binary`) описывает физическую природу признака;
- фактическое значение всегда задаётся распределением по конечным категориям;
- `unknown` означает нехватку сведений, а `not_relevant` — неприменимость драйвера;
- `evidence_status` отличает явные сведения от вывода и отсутствия информации;
- probabilities каждого применимого драйвера должны суммироваться в 1.
- взвешенная полнота считается как `1 - sum(cost_impact_percent * P(unknown)) / sum(cost_impact_percent)` по применимым драйверам.

## Применение requests to add

Notebook 3 по умолчанию работает в `review`: LLM формирует решение, но каталог не меняется. После просмотра `merge_decisions.jsonl` можно переключить `APPLY_MODE` на `auto`. В этом режиме применяются только решения не ниже `AUTO_APPLY_MIN_CONFIDENCE`; все изменения проходят повторную Pydantic-валидацию.

## Проверки

```bash
pytest -q
python -m compileall src
```
